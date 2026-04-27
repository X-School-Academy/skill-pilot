from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .agent import config_from_env, run_agent


REPO_ROOT = Path(__file__).resolve().parents[3]


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
    parser.add_argument("--log-level", default="info")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--bash-commands", default=None)
    parser.add_argument("--skills-dir", type=Path, default=None)
    parser.add_argument("--skills", default=None)
    parser.add_argument("prompt", nargs="*")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        parser.error("prompt is required")

    agent_dir = args.agent_dir.resolve()
    skills_dir = (args.skills_dir or (agent_dir / ".agent")).resolve()
    config = config_from_env(
        prompt=prompt,
        agent_dir=agent_dir,
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
        print(f"skill-pilot-agent error: {exc}", file=sys.stderr)
        return 1

    if output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
