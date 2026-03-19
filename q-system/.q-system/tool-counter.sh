#!/bin/bash
# Lightweight per-session tool call counter
# Called by PostToolUse hook. Tracks calls in /tmp, warns at thresholds.
# Companion to token-guard.py (which is heavier, runs on PreToolUse).

DATE=$(date +%Y%m%d)
COUNTER_FILE="/tmp/q-tool-counter-${DATE}.txt"

# Initialize if missing
if [ ! -f "$COUNTER_FILE" ]; then
  echo "0" > "$COUNTER_FILE"
fi

# Increment
COUNT=$(cat "$COUNTER_FILE")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"

# Thresholds
if [ $((COUNT % 10)) -eq 0 ]; then
  echo "TOKEN CHECK: $COUNT tool calls this session. Pause and ask: Am I closer to the goal than 10 calls ago?" >&2
fi

if [ "$COUNT" -eq 30 ]; then
  echo "WARNING: 30 tool calls. Consider pausing to ask the founder targeted questions before burning more tokens." >&2
fi

if [ "$COUNT" -eq 50 ]; then
  echo "WARNING: 50 tool calls. Run /q-challenge to verify you're not chasing assumptions." >&2
fi

exit 0
