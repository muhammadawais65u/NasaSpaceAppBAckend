create table public.nasa_events (
    id uuid primary key default gen_random_uuid(),
    source text not null default 'NASA DONKI',
    external_event_id text not null,
    event_type text not null check (event_type in ('CME','GST','FLR')),
    event_date timestamptz not null,
    event_data jsonb not null,
    summary jsonb not null,
    data_origin text not null default 'live_api'
        check (data_origin in ('live_api','archive')),
    retrieved_at timestamptz not null default now(),
    unique (source, external_event_id)
);
create index nasa_events_type_date_idx
    on public.nasa_events (event_type, event_date desc);

create table public.mission_runs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    mission_type text not null default 'lunar_outpost'
        check (mission_type in ('lunar_outpost','mars_outpost')),
    mission_status text not null default 'active'
        check (mission_status in ('active','completed','failed')),
    current_day int not null default 1 check (current_day >= 1),
    total_days int not null default 7 check (total_days >= 1),
    oxygen_level int not null check (oxygen_level between 0 and 100),
    power_level int not null check (power_level between 0 and 100),
    radiation_protection_level int not null
        check (radiation_protection_level between 0 and 100),
    score int not null default 0 check (score >= 0),
    alert_level text not null default 'calm'
        check (alert_level in ('calm','watch','storm')),
    scenario_event_id uuid references public.nasa_events(id) on delete set null,
    version int not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index mission_runs_user_idx
    on public.mission_runs (user_id, created_at desc);
create unique index one_active_mission_per_user
    on public.mission_runs (user_id) where mission_status = 'active';

create table public.decision_logs (
    id uuid primary key default gen_random_uuid(),
    mission_id uuid not null references public.mission_runs(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    nasa_event_id uuid references public.nasa_events(id) on delete set null,
    request_id uuid not null,
    day int not null check (day >= 1),
    decision_type text not null,
    selected_option text not null,
    resource_changes jsonb not null,
    score_change int not null,
    feedback text,
    state_after jsonb not null,
    created_at timestamptz not null default now(),
    unique (mission_id, request_id),
    unique (mission_id, day)
);
create index decision_logs_mission_idx on public.decision_logs (mission_id, day);

create or replace function public.set_updated_at() returns trigger
language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

create trigger mission_runs_updated_at before update on public.mission_runs
    for each row execute function public.set_updated_at();
