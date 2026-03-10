# Profile

## Brief

Editable user profile and preference data used to personalize learning and AI interactions.

## User Value

- Gives the product a stable place to store user-specific context.
- Supports known fields and custom fields in one model.
- Includes timezone data that can shape scheduling and personalization behavior.

## Main Behavior

- Loads profile data from backend config.
- Edits known fields and arbitrary custom keys.
- Adds or removes fields directly in the UI.
- Provides timezone search and selection support.
- Saves the resulting profile payload back to config storage.

## Related Features

- `ai-and-security.md`
- `learning.md`
- `schedules.md`

## Code References

- `core/webui/pages/index.tsx`
- `core/engine/routes.py`
- Keywords: `fetchProfile`, `profileSave`, `profileSetField`, `profileRemoveField`, `profileAddKnownField`, `profileAddCustomField`, `timezone`
- API routes: `/api/config/profile`

