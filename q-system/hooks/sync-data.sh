#!/usr/bin/env bash
# Sync instance data across plugin install variants.
#
# Claude Code uses different data dirs depending on install method:
#   kipi-system, kipi-system-inline, kipi-system-kipi-local, etc.
#
# This hook runs at SessionStart and ensures the current session's
# CLAUDE_PLUGIN_DATA has all instances and the active-instance file,
# regardless of which variant was used to install initially.
#
# Usage: sync-data.sh <CLAUDE_PLUGIN_DATA>

set -euo pipefail

CURRENT="$1"
PARENT="$(dirname "$CURRENT")"

[ -d "$PARENT" ] || exit 0

mkdir -p "$CURRENT/instances"

for alt_dir in "$PARENT"/kipi-system*; do
  [ -d "$alt_dir" ] || continue
  [ "$alt_dir" = "$CURRENT" ] && continue

  # Sync instances
  if [ -d "$alt_dir/instances" ]; then
    for inst in "$alt_dir/instances"/*/; do
      [ -d "$inst" ] || continue
      name="$(basename "$inst")"
      if [ ! -d "$CURRENT/instances/$name" ]; then
        cp -r "$inst" "$CURRENT/instances/$name"
      fi
    done
  fi

  # Sync active-instance file
  if [ -f "$alt_dir/active-instance" ] && [ ! -f "$CURRENT/active-instance" ]; then
    cp "$alt_dir/active-instance" "$CURRENT/active-instance"
  fi
done
