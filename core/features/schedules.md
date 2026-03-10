# Schedules

## Brief

Scheduler configuration view for recurring skill runs with provider selection and cron preview.

## User Value

- Turns ad hoc skill usage into repeatable scheduled runs.
- Makes schedule setup accessible from the UI without editing config files.
- Validates skills and providers before save.

## Main Behavior

- Lists saved schedules and opens them for editing.
- Creates or updates a schedule with frequency, time, provider, and enabled state.
- Shows cron preview and human-readable schedule text.
- Deletes schedules from the list.
- Uses skill and provider lookup to guard invalid values.

## Related Features

- `skills-management.md`
- `ai-and-security.md`
- `new-session.md`

## Code References

- `core/webui/pages/index.tsx`
- `core/engine/routes.py`
- `core/engine/scheduler.py`
- Keywords: `fetchSchedules`, `scheduleSave`, `scheduleDelete`, `scheduleStartEdit`, `formDataToCron`, `cronToHumanReadable`
- API routes: `/api/config/schedules`, `/api/config/schedules/{schedule_id}`

