create table if not exists public.diagnostic_items (
    id bigserial primary key,
    diagnostic_session_id text not null,
    student_id text not null,
    question_id text not null,
    skill_id text not null,
    domain text not null,
    cluster text not null,
    question_text text not null,
    question_order integer not null check (question_order > 0),
    student_answer text null,
    is_correct boolean not null,
    created_at timestamptz not null default timezone('utc', now()),
    constraint uq_diagnostic_items_session_order unique (diagnostic_session_id, question_order),
    constraint uq_diagnostic_items_session_question unique (diagnostic_session_id, question_id)
);

create index if not exists idx_diagnostic_items_session_id
    on public.diagnostic_items (diagnostic_session_id);

create index if not exists idx_diagnostic_items_student_id
    on public.diagnostic_items (student_id);

create index if not exists idx_diagnostic_items_skill_id
    on public.diagnostic_items (skill_id);

create table if not exists public.diagnostic_skill_estimates (
    id bigserial primary key,
    diagnostic_session_id text not null,
    student_id text not null,
    skill_id text not null,
    diagnostic_state text not null,
    estimated_mastery_probability numeric(4, 2) not null check (estimated_mastery_probability >= 0 and estimated_mastery_probability <= 1),
    mastery_status text not null check (mastery_status in ('mastered', 'learning', 'remediation')),
    student_mastery_status text not null check (student_mastery_status in ('mastered', 'learning', 'needs_review')),
    confidence_level text not null check (confidence_level in ('low', 'medium', 'high')),
    source text not null check (source in ('direct', 'propagated')),
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    constraint uq_diagnostic_skill_estimates_session_skill unique (diagnostic_session_id, skill_id)
);

create index if not exists idx_diagnostic_skill_estimates_session_id
    on public.diagnostic_skill_estimates (diagnostic_session_id);

create index if not exists idx_diagnostic_skill_estimates_student_id
    on public.diagnostic_skill_estimates (student_id);

create index if not exists idx_diagnostic_skill_estimates_skill_id
    on public.diagnostic_skill_estimates (skill_id);

create index if not exists idx_diagnostic_skill_estimates_mastery_status
    on public.diagnostic_skill_estimates (mastery_status);
