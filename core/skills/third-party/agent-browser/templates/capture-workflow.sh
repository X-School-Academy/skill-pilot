#!/bin/bash
# Template: Content Capture Workflow
# Purpose: Extract content from web pages (text, screenshots, PDF)
# Usage: ./capture-workflow.sh <url> [output-dir]
#
# Outputs:
#   - page-full.png: Full page screenshot
#   - page-structure.txt: Page element structure with refs
#   - page-text.txt: All text content
#   - page.pdf: PDF version
#
# Optional: Load auth state for protected pages

set -euo pipefail

TARGET_URL="${1:?Usage: $0 <url> [output-dir]}"
OUTPUT_DIR="${2:-.}"

echo "Capturing: $TARGET_URL"
mkdir -p "$OUTPUT_DIR"

# Optional: Load authentication state
# if [[ -f "./auth-state.json" ]]; then
#     echo "Loading authentication state..."
#     core/bin/agent-browser state load "./auth-state.json"
# fi

# Navigate to target
core/bin/agent-browser open "$TARGET_URL"
core/bin/agent-browser wait --load networkidle

# Get metadata
TITLE=$(core/bin/agent-browser get title)
URL=$(core/bin/agent-browser get url)
echo "Title: $TITLE"
echo "URL: $URL"

# Capture full page screenshot
core/bin/agent-browser screenshot --full "$OUTPUT_DIR/page-full.png"
echo "Saved: $OUTPUT_DIR/page-full.png"

# Get page structure with refs
core/bin/agent-browser snapshot -i > "$OUTPUT_DIR/page-structure.txt"
echo "Saved: $OUTPUT_DIR/page-structure.txt"

# Extract all text content
core/bin/agent-browser get text body > "$OUTPUT_DIR/page-text.txt"
echo "Saved: $OUTPUT_DIR/page-text.txt"

# Save as PDF
core/bin/agent-browser pdf "$OUTPUT_DIR/page.pdf"
echo "Saved: $OUTPUT_DIR/page.pdf"

# Optional: Extract specific elements using refs from structure
# core/bin/agent-browser get text @e5 > "$OUTPUT_DIR/main-content.txt"

# Optional: Handle infinite scroll pages
# for i in {1..5}; do
#     core/bin/agent-browser scroll down 1000
#     core/bin/agent-browser wait 1000
# done
# core/bin/agent-browser screenshot --full "$OUTPUT_DIR/page-scrolled.png"

# Cleanup
core/bin/agent-browser close

echo ""
echo "Capture complete:"
ls -la "$OUTPUT_DIR"
