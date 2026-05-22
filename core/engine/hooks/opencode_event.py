from dialog_recorder import record_event
from session_start import current_git_commit


if __name__ == "__main__":
    record_event("opencode_event", extra_metadata={"git_commit": current_git_commit()})
