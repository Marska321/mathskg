# Lumen Engine (CAPS Math Platform)

FastAPI backend for the CAPS-aligned mastery platform, including:
- diagnostic lifecycle APIs
- adaptive practice + mastery routing
- student report APIs
- teacher analytics APIs
- authoring APIs + authoring console

## 1. Local Setup

From project root (`C:\Users\User\Downloads\mathskg`):

```bat
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Environment Variables

Create `.env` (or copy from `.env.example`) and set:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
```

`SUPABASE_KEY` is still accepted as a legacy alias, but the API should prefer `SUPABASE_SERVICE_KEY`.

## 3. Run API

```bat
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 --env-file .env
```

## 4. Test

```bat
.\.venv\Scripts\python.exe -m pytest -q
```

Verify the live Supabase diagnostic setup with:

```bat
.\.venv\Scripts\python.exe scripts\check_diagnostic_supabase.py --write-probe
```

## 5. Key URLs

- Swagger docs: `http://localhost:8000/docs`
- Teacher dashboard: `http://localhost:8000/review`
- Authoring console: `http://localhost:8000/authoring/review`

## 6. Core API Groups

- Diagnostic: `/diagnostic/start`, `/diagnostic/answer`, `/diagnostic/result`
- Practice: `/generate-practice`, `/next-skill`, `/submit-answer`
- Student reports: `/students/{student_id}/mastery`, `/students/{student_id}/repair-path`, `/students/{student_id}/report`
- Teacher analytics: `/teacher/class/{class_id}/heatmap`, `/teacher/class/{class_id}/bottlenecks`, `/teacher/class/{class_id}/caps-coverage`
- Authoring: `/authoring/skills`, `/authoring/templates`, `/authoring/publish`

## 7. Diagnostic Schema

Run these SQL files in Supabase SQL editor, in order:

```sql
-- 1. sql/001_create_diagnostic_question_bank.sql
-- 2. sql/002_create_diagnostic_persistence_tables.sql
-- 3. sql/003_grant_diagnostic_api_privileges.sql
```

This creates:
- `diagnostic_question_bank`
- `diagnostic_items`
- `diagnostic_skill_estimates`

Seed the Grade 4 anchor bank with:

```bat
.\.venv\Scripts\python.exe scripts\seed_diagnostic_question_bank.py
```

Seed data lives in `data/grade4_diagnostic_question_bank.json`.

Note: the current Grade 4 graph does not yet expose dedicated decimal skill nodes. The decimal anchors are temporarily mapped to the nearest existing comparison, fraction, and measurement skills so the bank remains graph-linked until dedicated decimal nodes are added.

## 8. CI

GitHub Actions workflow is in `.github/workflows/tests.yml` and runs `pytest -q` on push and pull request.
