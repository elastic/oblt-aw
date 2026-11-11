# Routing: repo-scheduled

## Path

- `trigger-obs-aw-schedule-daily.yml` → `obs-aw-event-schedule.yml` (`schedule-profile: daily`) → `obs-aw-repo-scheduled.yml`
- `trigger-obs-aw-schedule-frequent.yml` → `obs-aw-event-schedule.yml` (`schedule-profile: frequent`) → `obs-aw-repo-scheduled.yml`
- `trigger-obs-aw-schedule-weekly.yml` → `obs-aw-event-schedule.yml` (`schedule-profile: weekly`) → `obs-aw-repo-scheduled.yml`

## Gates

1. Control Plane dashboard contains `obs:repo-scheduled`.
2. Event is `schedule` or `workflow_dispatch`.
3. Discovery finds at least one `.github/ai/scheduled/*.md` whose `schedule-profiles` includes the wake profile.
4. Requested capabilities have optional secrets present (for example `buildkite-logs` needs `BUILDKITE_LOGS_API_TOKEN`).

## References

- [obs-aw-repo-scheduled.md](../workflows/obs-aw-repo-scheduled.md)
