from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.database import supabase as supabase_client
from models.domain import MasteryStatus
from services.diagnostic_anchor_bank import build_anchor_prompt, select_anchor_question_for_skill
from services.diagnostic_engine import DiagnosticGraph, initialize_diagnostic_state, is_diagnostic_complete, process_diagnostic_answer
from services.diagnostic_orchestrator import (
    MAX_QUESTIONS,
    build_starting_skill_queue,
    extend_skill_queue,
    select_next_anchor_question,
)
from services.diagnostic_persistence import persist_diagnostic_item, persist_skill_estimates
from services.diagnostic_result import build_diagnostic_result
from services.diagnostic_session_store import (
    create_diagnostic_session,
    get_diagnostic_session,
    update_diagnostic_session,
)

router = APIRouter()
HARNESS_PATH = Path(__file__).resolve().parent.parent / 'diagnostic_harness.html'


class DiagnosticStartRequest(BaseModel):
    student_id: str


class DiagnosticAnswerRequest(BaseModel):
    session_id: str
    skill_id: str
    is_correct: bool
    student_answer: str | None = None


def _normalize_status(raw_value: str | None) -> str:
    if raw_value is None:
        return MasteryStatus.UNKNOWN.value
    try:
        return MasteryStatus(raw_value).value
    except ValueError:
        return MasteryStatus.UNKNOWN.value


def _get_all_skill_ids() -> list[str]:
    response = supabase_client.table('skills').select('skill_id').execute()
    return [skill['skill_id'] for skill in response.data]


def _get_edges() -> list[dict[str, str]]:
    response = (
        supabase_client.table('skill_prerequisites')
        .select('*')
        .execute()
    )
    edges: list[dict[str, str]] = []
    for row in response.data:
        prerequisite_id = row.get('prerequisite_id') or row.get('prerequisite_skill_id')
        if prerequisite_id:
            edges.append({'skill_id': row['skill_id'], 'prerequisite_id': prerequisite_id})
    return edges


def _load_student_state(student_id: str, all_skill_ids: list[str]) -> dict[str, str]:
    state_response = (
        supabase_client.table('student_mastery')
        .select('skill_id, status')
        .eq('student_id', student_id)
        .execute()
    )
    known_state = {
        row['skill_id']: _normalize_status(row.get('status'))
        for row in state_response.data
    }
    return {
        skill_id: known_state.get(skill_id, MasteryStatus.UNKNOWN.value)
        for skill_id in all_skill_ids
    }


def _build_graph() -> DiagnosticGraph:
    return DiagnosticGraph()


def _restore_graph_state(
    graph: DiagnosticGraph,
    current_state: dict[str, str],
    asked_skill_ids: list[str],
) -> None:
    graph.tested_skill_ids.update(asked_skill_ids)
    graph.assumed_known_skill_ids.update(
        skill_id
        for skill_id, state in current_state.items()
        if state in {MasteryStatus.MASTERED.value, MasteryStatus.ASSUMED_MASTERED.value}
    )


def _fetch_anchor_for_skill(skill_id: str):
    return select_anchor_question_for_skill(skill_id, repository=supabase_client)


def _complete_session_response(
    session_id: str,
    current_state: dict[str, str],
    question_count: int,
    student_id: str | None = None,
    message: str | None = None,
) -> dict:
    result = build_diagnostic_result(current_state, question_count)
    payload = {
        'status': 'complete',
        'session_id': session_id,
        **result,
    }
    if student_id is not None:
        payload['student_id'] = student_id
    if message:
        payload['message'] = message
    return payload


def _persist_completion(
    session_id: str,
    student_id: str,
    current_state: dict[str, str],
    question_count: int,
    asked_skills: list[str],
    message: str | None = None,
) -> dict:
    payload = _complete_session_response(
        session_id,
        current_state,
        question_count,
        student_id=student_id,
        message=message,
    )
    persist_skill_estimates(supabase_client, session_id, student_id, current_state)
    saved = update_diagnostic_session(
        session_id,
        {
            'status': 'complete',
            'current_state': current_state,
            'question_count': question_count,
            'asked_skills': asked_skills,
            'pending_skill_ids': [],
            'active_question': None,
            'placement_skill_id': payload['placement_skill_id'],
            'confidence': payload['confidence'],
            'next_skill_id': None,
        },
    )
    if saved is None:
        raise HTTPException(status_code=500, detail='Failed to update diagnostic session.')
    return payload


@router.post('/diagnostic/start')
async def diagnostic_start(request: DiagnosticStartRequest):
    try:
        graph = _build_graph()
        all_skill_ids = graph.get_sorted_skill_ids()
        if not all_skill_ids:
            raise HTTPException(status_code=404, detail='No skills found for diagnostic.')

        initial_state = initialize_diagnostic_state(all_skill_ids)
        student_state = _load_student_state(request.student_id, all_skill_ids)
        current_state = {
            skill_id: student_state.get(skill_id, initial_state[skill_id])
            for skill_id in all_skill_ids
        }

        starting_queue = build_starting_skill_queue(graph, current_state)
        next_skill_id, anchor, remaining_queue = select_next_anchor_question(
            graph,
            current_state,
            starting_queue,
            [],
            _fetch_anchor_for_skill,
        )

        session = create_diagnostic_session(
            request.student_id,
            current_state,
            pending_skill_ids=remaining_queue,
            active_question=anchor.model_dump() if anchor is not None else None,
        )
        if session is None:
            raise HTTPException(status_code=500, detail='Failed to create diagnostic session.')

        if not next_skill_id or anchor is None:
            return _persist_completion(
                session['session_id'],
                request.student_id,
                current_state,
                question_count=0,
                asked_skills=[],
                message='Diagnostic already complete for available anchor questions.',
            )

        session = update_diagnostic_session(
            session['session_id'],
            {
                'pending_skill_ids': remaining_queue,
                'active_question': anchor.model_dump(),
                'next_skill_id': next_skill_id,
            },
        )
        if session is None:
            raise HTTPException(status_code=500, detail='Failed to update diagnostic session.')

        return {
            'status': 'in_progress',
            'session_id': session['session_id'],
            'next_skill': next_skill_id,
            'next_skill_id': next_skill_id,
            'question_count': session['question_count'],
            'max_questions': MAX_QUESTIONS,
            'question': build_anchor_prompt(anchor),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post('/diagnostic/answer')
async def diagnostic_answer(request: DiagnosticAnswerRequest):
    try:
        session = get_diagnostic_session(request.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail='Diagnostic session not found.')

        if session.get('status') == 'complete':
            return _complete_session_response(
                session['session_id'],
                session.get('current_state') or {},
                session.get('question_count') or 0,
                student_id=session.get('student_id'),
            )

        current_state = session.get('current_state') or {}
        active_question = session.get('active_question')
        asked_skills = [*(session.get('asked_skills') or []), request.skill_id]
        pending_skill_ids = session.get('pending_skill_ids') or []

        updated_state = process_diagnostic_answer(
            request.skill_id,
            request.is_correct,
            current_state,
            _get_edges(),
        )
        question_count = (session.get('question_count') or 0) + 1

        if active_question is not None:
            persist_diagnostic_item(
                supabase_client,
                diagnostic_session_id=session['session_id'],
                student_id=session['student_id'],
                question_order=question_count,
                anchor=active_question,
                student_answer=request.student_answer,
                is_correct=request.is_correct,
            )

        graph = _build_graph()
        _restore_graph_state(graph, current_state, session.get('asked_skills') or [])
        candidate_skill_ids = graph.evaluate_answer(request.skill_id, request.is_correct)
        pending_skill_ids = extend_skill_queue(
            pending_skill_ids,
            candidate_skill_ids,
            updated_state,
            asked_skills,
        )

        if is_diagnostic_complete(updated_state, question_count, max_questions=MAX_QUESTIONS):
            return _persist_completion(
                session['session_id'],
                session['student_id'],
                updated_state,
                question_count,
                asked_skills,
            )

        next_skill_id, anchor, remaining_queue = select_next_anchor_question(
            graph,
            updated_state,
            pending_skill_ids,
            asked_skills,
            _fetch_anchor_for_skill,
        )

        if next_skill_id is None or anchor is None:
            return _persist_completion(
                session['session_id'],
                session['student_id'],
                updated_state,
                question_count,
                asked_skills,
                message='Diagnostic ended because no anchor questions remain.',
            )

        saved = update_diagnostic_session(
            session['session_id'],
            {
                'status': 'in_progress',
                'current_state': updated_state,
                'question_count': question_count,
                'asked_skills': asked_skills,
                'pending_skill_ids': remaining_queue,
                'active_question': anchor.model_dump(),
                'next_skill_id': next_skill_id,
            },
        )
        if saved is None:
            raise HTTPException(status_code=500, detail='Failed to update diagnostic session.')

        return {
            'status': 'in_progress',
            'session_id': session['session_id'],
            'next_skill': next_skill_id,
            'next_skill_id': next_skill_id,
            'question_count': question_count,
            'max_questions': MAX_QUESTIONS,
            'question': build_anchor_prompt(anchor),
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/diagnostic/harness', include_in_schema=False)
async def diagnostic_harness():
    if not HARNESS_PATH.exists():
        raise HTTPException(status_code=404, detail='Diagnostic harness not found.')
    return FileResponse(HARNESS_PATH)


@router.get('/diagnostic/result')
async def diagnostic_result(session_id: str = Query(..., description='Diagnostic session id')):
    try:
        session = get_diagnostic_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail='Diagnostic session not found.')

        result = build_diagnostic_result(
            session.get('current_state') or {},
            session.get('question_count') or 0,
        )

        if session.get('placement_skill_id') is None and result['placement_skill_id'] is not None:
            update_diagnostic_session(
                session['session_id'],
                {
                    'placement_skill_id': result['placement_skill_id'],
                    'confidence': result['confidence'],
                },
            )

        return {
            'status': session.get('status', 'in_progress'),
            'session_id': session['session_id'],
            'student_id': session['student_id'],
            'next_skill': session.get('next_skill_id'),
            'max_questions': MAX_QUESTIONS,
            **result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post('/diagnostic/next-question')
async def get_next_question(request: DiagnosticStartRequest):
    return await diagnostic_start(request)

