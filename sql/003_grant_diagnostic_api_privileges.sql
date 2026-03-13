grant usage on schema public to service_role;

grant select, insert, update, delete on table public.diagnostic_question_bank to service_role;
grant select, insert, update, delete on table public.diagnostic_items to service_role;
grant select, insert, update, delete on table public.diagnostic_skill_estimates to service_role;

grant usage, select on sequence public.diagnostic_items_id_seq to service_role;
grant usage, select on sequence public.diagnostic_skill_estimates_id_seq to service_role;
