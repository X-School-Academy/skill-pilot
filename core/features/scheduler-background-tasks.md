# Feature Retrieval Index: Scheduler and Background Tasks

## Retrieval Keywords

scheduler, background tasks, cron, schedule, scheduled tasks, schedule-course, schedule agent, task scheduler, scheduler.py, core/schedule, remote agent schedule, routines, cron job

## Scope

- Background task scheduling in the engine
- Scheduled agent skill runs (routines)
- Course scheduling skill
- Excludes: workflow execution (separate), tmux background sessions (see terminal feature)

## Main Behavior

- `core/engine/scheduler.py` manages periodic background tasks within the engine process
- `core/schedule/` stores scheduled agent routine definitions
- `schedule-course` skill schedules recurring course delivery
- Background tasks support periodic polling, cleanup, and agent runs

## Code Map

- `core/engine/scheduler.py` — background task scheduler
- `core/schedule/` — scheduled routine definitions directory
- `core/skills/system/schedule-course/` — course scheduling skill

## Search Commands

```bash
cat core/engine/scheduler.py | head -40
ls core/schedule/
find core/skills/system/schedule-course/ -type f
```

## Related Features

- `core/features/course-creator.md`
- `core/features/workflow-runner-editor.md`
- `core/features/skill-agent-system.md`

## Update Notes

- `core/schedule/` stores user-defined scheduled routines; preserve on upgrades
- Scheduler starts automatically with the engine; check `scheduler.py` for interval configuration
