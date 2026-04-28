import argparse
import asyncio
import logging
import os
from pathlib import Path
from typing import Any, List, Optional

from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, function_tool
from agents.run import Runner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@function_tool
async def execute_bash(commands: str) -> str:
    """Executes a bash script and returns its stdout, stderr, and exit code.
    
    Args:
        commands: The bash script or commands to execute.
    """
    process = await asyncio.create_subprocess_shell(
        commands,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    
    out = ""
    if stdout:
        out += f"STDOUT:\n{stdout.decode('utf-8', errors='replace')}\n"
    if stderr:
        out += f"STDERR:\n{stderr.decode('utf-8', errors='replace')}\n"
    out += f"EXIT CODE: {process.returncode}"
    return out

def main():
    parser = argparse.ArgumentParser(description="Skill Pilot Agent")
    parser.add_argument("prompt", nargs="*", help="The prompt to execute")
    parser.add_argument("--sandbox", choices=["yes", "no"], default="yes", help="Enable sandbox")
    parser.add_argument("--auto", choices=["yes", "no"], default="yes", help="Enable auto tools")
    parser.add_argument("--network", choices=["yes", "no"], default="no", help="Enable network")
    parser.add_argument("--model", type=str, default=os.getenv("SKILL_PILOT_MODEL", "gpt-4o"))
    parser.add_argument("--agent-dir", type=str, default=".")
    parser.add_argument("--log-level", type=str, default="info")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--bash-commands", type=str, default="")
    parser.add_argument("--skills-dir", type=str, default=".agent")
    parser.add_argument("--skills", type=str, default="")
    
    args = parser.parse_args()
    
    level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    prompt = " ".join(args.prompt) if args.prompt else ""
    if not prompt:
        logger.warning("No prompt provided. Exiting.")
        return
        
    if args.network == "no":
        logger.warning("openai-agents does not support strict OS-level network enforcement for local execution. Network access remains enabled.")
        
    agent_dir = Path(args.agent_dir).resolve()
    
    # Read root AGENTS.md directly from agent-dir
    agents_file = agent_dir / "AGENTS.md"
    system_prompt = ""
    if agents_file.is_file():
        system_prompt = agents_file.read_text(encoding="utf-8")
        
    # Read skills
    skills_dir_path = Path(args.skills_dir)
    if not skills_dir_path.is_absolute():
        skills_dir_path = agent_dir / skills_dir_path
        
    selected_skills = [s.strip() for s in args.skills.split(",")] if args.skills else None
    
    if skills_dir_path.is_dir():
        for skill_dir in skills_dir_path.iterdir():
            if skill_dir.is_dir():
                skill_name = skill_dir.name
                if selected_skills is None or skill_name in selected_skills:
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.is_file():
                        system_prompt += f"\n\n--- SKILL: {skill_name} ---\n{skill_file.read_text(encoding='utf-8')}"
                        
    # Initialize OpenAI client with custom endpoint
    base_url = os.getenv("SKILL_PILOT_BASE_URL")
    api_key = os.getenv("SKILL_PILOT_API_KEY", "not-needed")
    
    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    model = OpenAIChatCompletionsModel(model=args.model, openai_client=client)
    
    # We pass the tool wrapped in function_tool
    tool = execute_bash
    
    agent = Agent(
        name="Skill Pilot Agent",
        instructions=system_prompt,
        tools=[tool],
        model=model,
    )
    
    logger.info(f"Running agent with model {args.model} and base_url {base_url}")
    result = Runner.run_sync(agent, input=prompt, max_turns=args.max_retries)
    
    print(result.final_output)

if __name__ == "__main__":
    main()