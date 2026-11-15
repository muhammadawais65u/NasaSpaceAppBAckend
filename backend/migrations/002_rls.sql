alter table public.mission_runs enable row level security;
alter table public.decision_logs enable row level security;
alter table public.nasa_events enable row level security;

-- Players may READ their own rows only.
create policy "players read own missions" on public.mission_runs
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "players read own decisions" on public.decision_logs
  for select to authenticated using ((select auth.uid()) = user_id);
-- NASA events are shared reference data: any signed-in user may read.
create policy "signed-in users read nasa events" on public.nasa_events
  for select to authenticated using (true);

-- No insert/update/delete policies exist, so clients cannot write.
-- The backend writes with the service-role key, which bypasses RLS.
revoke insert, update, delete on public.mission_runs, public.decision_logs,
  public.nasa_events from anon, authenticated;
revoke select on public.mission_runs, public.decision_logs,
  public.nasa_events from anon;
