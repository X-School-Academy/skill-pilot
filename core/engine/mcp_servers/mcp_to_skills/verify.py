#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path
import yaml

def verify_skill(skill_dir: Path) -> list[str]:
    errors = []
    if not skill_dir.is_dir():
        return [f"'{skill_dir}' is not a directory"]

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"Missing SKILL.md in '{skill_dir}'"]

    try:
        content = skill_md.read_text()
    except Exception as e:
        return [f"Failed to read SKILL.md: {e}"]

    if not content.startswith("---"):
        return ["SKILL.md must start with YAML frontmatter (---)"]

    try:
        # Split by --- and get the second part (frontmatter)
        # We use split('---', 2) to get:
        # 0: empty string (before first ---)
        # 1: frontmatter
        # 2: body
        parts = content.split("---", 2)
        if len(parts) < 3:
            return ["Invalid SKILL.md format: missing closing --- for frontmatter"]
        
        frontmatter_raw = parts[1]
        frontmatter = yaml.safe_load(frontmatter_raw)
    except Exception as e:
        return [f"Failed to parse YAML frontmatter: {e}"]

    if not isinstance(frontmatter, dict):
        return ["Frontmatter must be a YAML object"]

    # Check 'name'
    name = frontmatter.get("name")
    if not name:
        errors.append("Missing 'name' in frontmatter")
    elif not isinstance(name, str):
        errors.append("'name' in frontmatter must be a string")
    else:
        if name != skill_dir.name:
            errors.append(f"'name' in frontmatter ('{name}') does not match directory name ('{skill_dir.name}')")
        
        # Specification: 1-64 chars, lowercase alphanumeric and hyphens, 
        # not start or end with hyphen, no consecutive hyphens.
        if not re.match(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$", name) or "--" in name:
            errors.append(f"Invalid 'name' format: '{name}'")

    # Check 'description'
    description = frontmatter.get("description")
    if not description:
        errors.append("Missing 'description' in frontmatter")
    elif not isinstance(description, str):
        errors.append("'description' in frontmatter must be a string")
    elif len(description) > 1024:
        errors.append("'description' is too long (max 1024 characters)")

    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an agent skill against the specification")
    parser.add_argument("skill_paths", type=Path, nargs="+", help="Path(s) to the skill directory or SKILL.md file")
    args = parser.parse_args()

    overall_success = True
    for path in args.skill_paths:
        target_path = path
        if target_path.is_file() and target_path.name == "SKILL.md":
            target_path = target_path.parent

        errors = verify_skill(target_path)
        if errors:
            print(f"Verification FAILED for '{target_path}':")
            for error in errors:
                print(f"  - {error}")
            overall_success = False
        else:
            print(f"Verification PASSED for '{target_path}'")
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    sys.exit(main())
