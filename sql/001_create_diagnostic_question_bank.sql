create table if not exists public.diagnostic_question_bank (
    question_id text primary key,
    grade_level integer not null check (grade_level between 1 and 12),
    domain text not null,
    cluster text not null,
    skill_id text not null,
    question_text text not null,
    correct_answer text not null,
    difficulty numeric(3, 1) not null default 1.0 check (difficulty >= 0.1 and difficulty <= 5.0),
    active boolean not null default true,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_diagnostic_question_bank_grade_level
    on public.diagnostic_question_bank (grade_level);

create index if not exists idx_diagnostic_question_bank_skill_id
    on public.diagnostic_question_bank (skill_id);

create index if not exists idx_diagnostic_question_bank_domain_cluster
    on public.diagnostic_question_bank (domain, cluster);
