#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Import from the engine package
try:
    from llm_service import llm_get_text, get_default_llm_provider_id
    from settings import PROJECT_DIR
except ImportError:
    # Fallback for different execution contexts
    engine_dir = Path(__file__).resolve().parent.parent.parent
    sys.path.append(str(engine_dir))
    from llm_service import llm_get_text, get_default_llm_provider_id
    from settings import PROJECT_DIR

def verify_assertion(output: str, assertion: str) -> bool:
    return assertion.lower() in output.lower()

def run_eval(skill_dir: Path):
    evals_file = skill_dir / "evals" / "evals.json"
    if not evals_file.exists():
        print(f"No evals found at {evals_file}")
        return

    try:
        eval_data = json.loads(evals_file.read_text())
    except Exception as e:
        print(f"Error reading evals.json: {e}")
        return

    skill_md = skill_dir / "SKILL.md"
    skill_context = ""
    if skill_md.exists():
        skill_context = f"\n\nContext from SKILL.md:\n{skill_md.read_text()}\n"

    provider_id = get_default_llm_provider_id()
    print(f"Using default provider: {provider_id}")
    print(f"Running {len(eval_data.get('evals', []))} evaluations for {skill_dir.name}...\n")

    passed_count = 0
    total_count = 0

    for i, eval_case in enumerate(eval_data.get("evals", [])):
        total_count += 1
        prompt = eval_case.get("prompt")
        assertions = eval_case.get("assertions", [])

        print(f"Eval {i+1}: {prompt[:60]}...")
        
        full_prompt = f"System Instruction: You are an expert agent using the following skill rules.{skill_context}\n\nUser Request: {prompt}"
        
        try:
            # Use llm_get_text from llm_service which handles provider selection and JSON output parsing
            output = llm_get_text(
                messages=[{"role": "user", "content": full_prompt}],
                provider_id=provider_id
            )
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            continue
        
        case_passed = True
        failed_assertions = []
        for assertion in assertions:
            if not verify_assertion(output, assertion):
                case_passed = False
                failed_assertions.append(assertion)
        
        if case_passed:
            print("  ✅ PASSED")
            passed_count += 1
        else:
            print("  ❌ FAILED")
            for fa in failed_assertions:
                print(f"    - Failed assertion: {fa}")
            # Optionally print output on failure for debugging
            # print(f"    Output: {output[:200]}...")

    print(f"\nSummary: {passed_count}/{total_count} evals passed.")

def main():
    parser = argparse.ArgumentParser(description="Run agent skill evaluations")
    parser.add_argument("skill_path", type=Path, help="Path to the skill directory")
    args = parser.parse_args()

    skill_dir = args.skill_path
    if not skill_dir.is_dir():
        # Try relative to project root
        if (PROJECT_DIR / skill_dir).is_dir():
            skill_dir = PROJECT_DIR / skill_dir
        else:
            print(f"Error: {skill_dir} is not a directory.")
            sys.exit(1)

    run_eval(skill_dir)

if __name__ == "__main__":
    main()
