#!/usr/bin/env python3
"""Audit always-on instruction token budget.

Single budget: CLAUDE.md (with imports) + effectively-always-on rules < 300 lines.

IMPORTANT: Rules with paths: ["**/*"] are functionally always-on because **/*
matches every file Claude will ever read. The script must count these as always-on,
not conditional. A naive has_paths_frontmatter() check would misclassify them.

Exits non-zero if budget exceeded.
"""
import os
import re
import sys

QROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROJECT_ROOT = os.path.normpath(os.path.join(QROOT, ".."))

# Anthropic docs say <200 for CLAUDE.md (stated 3x).
# Docs also say: "Rules without paths frontmatter are loaded at launch
# with the same priority as .claude/CLAUDE.md."
# Rules with paths: ["**/*"] match everything = same as no paths.
# Single budget: CLAUDE.md + effectively-always-on rules combined.
BUDGET_CLAUDE_MD = 200
BUDGET_TOTAL_ALWAYS_ON = 300

# Glob patterns that match everything (functionally always-on)
CATCH_ALL_PATTERNS = {"**/*", "**/**", "**"}


def count_lines(path):
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def parse_paths_from_frontmatter(path):
    """Extract paths/globs list from YAML frontmatter. Returns None if no scoping key."""
    with open(path) as f:
        content = f.read()

    if not content.startswith("---"):
        return None

    end = content.find("---", 3)
    if end == -1:
        return None

    frontmatter = content[3:end]
    # Check for either paths: or globs: (both are scoping keys in Claude Code)
    has_scoping = re.search(r"^(paths|globs):", frontmatter, re.MULTILINE)
    if not has_scoping:
        return None

    # Extract list values from whichever key is present
    paths = []
    in_list = False
    for line in frontmatter.splitlines():
        if re.match(r"^(paths|globs):\s*$", line):
            in_list = True
            continue
        if in_list:
            m = re.match(r'^\s+-\s+"?([^"]+)"?\s*$', line)
            if m:
                paths.append(m.group(1).strip())
            else:
                break
    return paths


def is_effectively_always_on(path):
    """Return True if the rule has no paths: or paths: contains a catch-all glob."""
    paths = parse_paths_from_frontmatter(path)

    # No paths key = always-on
    if paths is None:
        return True

    # Empty paths list = always-on (no restriction)
    if len(paths) == 0:
        return True

    # If ANY pattern is a catch-all, the rule is effectively always-on
    for p in paths:
        if p.strip().strip('"').strip("'") in CATCH_ALL_PATTERNS:
            return True

    return False


def resolve_imports(path):
    """Count lines including @import targets."""
    total = count_lines(path)
    if not os.path.exists(path):
        return total
    with open(path) as f:
        for line in f:
            match = re.match(r"^@(.+)$", line.strip())
            if match:
                import_path = os.path.join(os.path.dirname(path), match.group(1))
                total += count_lines(import_path)
    return total


def main():
    claude_md = os.path.join(PROJECT_ROOT, "CLAUDE.md")
    rules_dir = os.path.join(PROJECT_ROOT, ".claude", "rules")

    claude_md_lines = resolve_imports(claude_md)

    always_on_rules = 0
    always_on_files = []
    conditional_files = []
    for f in sorted(os.listdir(rules_dir)):
        if not f.endswith(".md"):
            continue
        fpath = os.path.join(rules_dir, f)
        lines = count_lines(fpath)
        if is_effectively_always_on(fpath):
            always_on_rules += lines
            always_on_files.append((f, lines))
        else:
            conditional_files.append((f, lines))

    total = claude_md_lines + always_on_rules

    print(f"CLAUDE.md (with imports): {claude_md_lines} / {BUDGET_CLAUDE_MD}")
    print(f"Always-on rules ({len(always_on_files)} files):")
    for name, lines in always_on_files:
        print(f"  {name}: {lines}")
    print(f"Conditional rules ({len(conditional_files)} files):")
    for name, lines in conditional_files:
        print(f"  {name}: {lines}")
    print(f"Total always-on (CLAUDE.md + rules): {total} / {BUDGET_TOTAL_ALWAYS_ON}")

    failed = False
    if claude_md_lines > BUDGET_CLAUDE_MD:
        print(
            f"\nFAIL: CLAUDE.md exceeds {BUDGET_CLAUDE_MD}-line budget "
            f"by {claude_md_lines - BUDGET_CLAUDE_MD} lines"
        )
        failed = True
    if total > BUDGET_TOTAL_ALWAYS_ON:
        print(
            f"\nFAIL: Total always-on exceeds {BUDGET_TOTAL_ALWAYS_ON}-line budget "
            f"by {total - BUDGET_TOTAL_ALWAYS_ON} lines"
        )
        failed = True

    if not failed:
        print("\nPASS: All budgets within limits")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
