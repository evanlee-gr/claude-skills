#!/bin/bash
# claude-skills/setup.sh
# Installs all Claude Code skills globally on macOS/Linux
# Usage: bash setup.sh

SKILLS_SOURCE="$(dirname "$0")/.claude/skills"
SKILLS_DEST="$HOME/.claude/skills"

echo "Claude Skills Installer"
echo "======================="
echo "Source: $SKILLS_SOURCE"
echo "Destination: $SKILLS_DEST"
echo ""

mkdir -p "$SKILLS_DEST"
count=0

for skill_dir in "$SKILLS_SOURCE"/*/; do
    skill_name=$(basename "$skill_dir")
    dest="$SKILLS_DEST/$skill_name"
    if [ -d "$dest" ]; then
        echo "Updating: $skill_name"
        rm -rf "$dest"
    else
        echo "Installing: $skill_name"
    fi
    cp -r "$skill_dir" "$dest"
    count=$((count + 1))
done

echo ""
echo "$count skills installed to $SKILLS_DEST"
echo "Claude Code will pick them up on next session."