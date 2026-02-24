#!/usr/bin/env python3
"""
Wrapper script that runs main.py and extracts only the <output>...</output> content.
Usage: ./run.py [all the same arguments as main.py]
"""
import subprocess
import sys
import re
import os
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent.resolve()
main_py = script_dir / "main.py"

# Run main.py with all arguments passed to this script
cmd = [str(main_py)] + sys.argv[1:]
result = subprocess.run(cmd, capture_output=True, text=True)

# Get the combined output
output = result.stdout

# Try to extract content between <output> and </output>
match = re.search(r'<output>(.*?)</output>', output, re.DOTALL)
if match:
    print(match.group(1).strip())
elif '</think>' in output:
    # Fallback: extract after </think>
    print(output.split('</think>', 1)[1].strip())
else:
    # Last resort: print everything (in case format changes)
    print(output.strip())

# Exit with same code as main.py
sys.exit(result.returncode)
