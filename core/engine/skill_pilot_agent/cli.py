from __future__ import annotations

import argparse
import sys
from pathlib import Path

from logger import get_logger

from .agent import config_from_env, run_agent


REPO_ROOT = Path(__file__).resolve().parents[3]

logger = get_logger("skill-pilot-agent")


def yes_no(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered == "yes":
        return True
    if lowered == "no":
        return False
    raise argparse.ArgumentTypeError("expected yes or no")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-pilot-agent")
    parser.add_argument("--sandbox", type=yes_no, metavar="yes|no", default=True)
    parser.add_argument("--auto", type=yes_no, metavar="yes|no", default=True)
    parser.add_argument("--network", type=yes_no, metavar="yes|no", default=False)
    parser.add_argument("--model", default=None)
    parser.add_argument("--agent-dir", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--agent-file",
        default="AGENTS.md",
        help="Agent instructions file relative to --agent-dir, an absolute path, or 'none' to skip.",
    )
    parser.add_argument("--log-level", default="info")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--bash-commands", default=None)
    parser.add_argument("--skills-dir", type=Path, default=None)
    parser.add_argument(
        "--skills",
        default=None,
        help="Comma-separated skills to load, or 'none' to skip all skills.",
    )
    parser.add_argument("prompt", nargs="*")
    return parser


def _resolve_agent_file(agent_dir: Path, agent_file: str) -> Path | None:
    value = (agent_file or "").strip()
    if not value or value.lower() == "none":
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = agent_dir / candidate
    return candidate.resolve()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    level_name = str(args.log_level).upper()
    logger.setLevel(level_name if level_name else "INFO")

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        parser.error("prompt is required")

    agent_dir = args.agent_dir.resolve()
    skills_dir = (args.skills_dir or (agent_dir / ".agent")).resolve()
    agent_file = _resolve_agent_file(agent_dir, args.agent_file)
    config = config_from_env(
        prompt=prompt,
        agent_dir=agent_dir,
        agent_file=agent_file,
        skills_dir=skills_dir,
        skills=args.skills,
        model=args.model,
        sandbox=args.sandbox,
        auto=args.auto,
        network=args.network,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
        bash_commands=args.bash_commands,
    )

    try:
        output = run_agent(config)
    except Exception as exc:
        logger.error("skill-pilot-agent failed: %s", exc)
        print(f"skill-pilot-agent error: {exc}", file=sys.stderr)
        return 1

    if output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
