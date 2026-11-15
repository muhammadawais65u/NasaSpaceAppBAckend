-- Adds the water and food resources (5 resources, 7 themed missions).
alter table public.mission_runs
    add column water_level int not null default 65 check (water_level between 0 and 100),
    add column food_level int not null default 65 check (food_level between 0 and 100);

create or replace function public.save_decision(
    p_mission_id uuid, p_user_id uuid, p_expected_version int,
    p_new_state jsonb, p_log jsonb
) returns public.mission_runs
language plpgsql security invoker as $$
declare v_row public.mission_runs;
begin
    update public.mission_runs set
        current_day = (p_new_state->>'current_day')::int,
        mission_status = p_new_state->>'mission_status',
        oxygen_level = (p_new_state->>'oxygen_level')::int,
        power_level = (p_new_state->>'power_level')::int,
        water_level = (p_new_state->>'water_level')::int,
        food_level = (p_new_state->>'food_level')::int,
        radiation_protection_level =
            (p_new_state->>'radiation_protection_level')::int,
        score = (p_new_state->>'score')::int,
        version = version + 1
    where id = p_mission_id and user_id = p_user_id
        and version = p_expected_version and mission_status = 'active'
    returning * into v_row;

    if not found then
        raise exception 'version_conflict';
    end if;

    insert into public.decision_logs (mission_id, user_id, nasa_event_id,
        request_id, day, decision_type, selected_option, resource_changes,
        score_change, feedback, state_after)
    values (p_mission_id, p_user_id,
        nullif(p_log->>'nasa_event_id','')::uuid,
        (p_log->>'request_id')::uuid, (p_log->>'day')::int,
        p_log->>'decision_type', p_log->>'selected_option',
        p_log->'resource_changes', (p_log->>'score_change')::int,
        p_log->>'feedback', to_jsonb(v_row));

    return v_row;
end $$;
