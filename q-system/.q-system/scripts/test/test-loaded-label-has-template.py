#!/usr/bin/env python3
"""Every loaded com.kipi.* label has a committed template (ASK-1345, sp-173ead80).

THE GAP. Measured on the founder's machine 2026-09-07:

    loaded com.kipi.* labels ........... 15
    committed templates ................ 15
    loaded with NO committed template ... 3
      com.kipi.audit-rotate    loaded 2026-05-18
      com.kipi.launchd-health  loaded 2026-06-30
      com.kipi.pr86-review     loaded 2026-08-07

None of the three had ever been added: `git log --all --diff-filter=A` over 3140
commits returns nothing for any of those basenames, and no copy sat in any stale
worktree. A machine rebuild loses them silently, and `install-plist.sh --all`
cannot install what is not committed. The existing coverage test
(test-install-jobs-coverage.py) walks the OTHER direction, committed -> installed,
so this population was structurally invisible to it.

com.kipi.launchd-health is fixed additively in the same change: its template is
now committed, transcribed from the live copy. The other two are ALLOWLISTED
below with a date and a reason rather than silently tolerated, because removing a
running job is the founder's call, not this script's.

WHY AN ALLOWLIST AND NOT A CLEAN GATE. A gate that is red on its own population
on day one gets switched off, and a gate that is off protects nothing. With the
two entries below this exits 0 on this machine today, which is the only condition
under which it is worth shipping.

THE ENUMERATOR IS BORROWED, NOT REBUILT. The committed set comes from
install-plist.sh's own usage listing, not from a second `git ls-files` written
here. Two enumerators for one question drift, and the drift is invisible until
the day they disagree -- which is the defect class this whole change is about.

HONEST BOUNDARY. It checks that a template EXISTS for a loaded label. It does not
check that the template would render to the job that is actually loaded: a
template whose schedule or program has drifted from the live copy passes here.
It is scoped to the `com.kipi.` prefix, so a com.cole.* or com.claudedaddy.* job
with no template is outside what this number covers.

Run: python3 q-system/.q-system/scripts/test/test-loaded-label-has-template.py
Exit 0 = pass. Exit 1 = a loaded label has no template and no allowlist entry.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
INSTALLER = REPO / "q-system" / ".q-system" / "scripts" / "install-plist.sh"
PREFIX = "com.kipi."

# EXEMPTIONS ARE WRITTEN DECISIONS, NOT SILENCE. Each entry names the date it was
# granted and what was measured. An entry earns removal by the label getting a
# template or by the founder unloading the job; neither is this script's call.
ALLOWLIST = {
    "com.kipi.audit-rotate": (
        "2026-09-07: rotates ~/.claude/audit/*.log nightly at 23:55. Its program "
        "lives entirely outside this repo (a 347-byte script in the founder's "
        "global Claude config, present and executable, created 2026-05-18) and "
        "nothing in the repo references it. A template here would point at a "
        "script a machine rebuild does not restore, which is half a fix wearing "
        "the shape of a whole one. Needs a founder decision: adopt the script "
        "into the repo, or leave the job machine-local."
    ),
    "com.kipi.pr86-review": (
        "2026-09-07: a ONE-SHOT job for PR #86, hourly at :17, that self-disables "
        "once a review completes or #86 leaves OPEN. Measured 2026-09-07: #86 is "
        "still OPEN, so the job is doing exactly what it was built to do. "
        "Committing a template for a job designed to delete itself would "
        "resurrect it on every fresh checkout. Expected to age out on its own."
    ),
}


def loaded_labels():
    """Labels launchd currently has bootstrapped, for this prefix.

    None (not an empty list) when there is no launchd to ask. CI runs on Linux,
    where `launchctl` does not exist: an empty set there would read as "no loaded
    label lacks a template" and this check would report a clean pass about a
    population it never saw. Distinguishing the two is the whole point.
    """
    if shutil.which("launchctl") is None:
        return None
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True,
                         timeout=60).stdout
    return sorted(set(re.findall(r"com\.kipi\.[A-Za-z0-9_.-]+", out)))


def committed_labels():
    """The installer's OWN enumerator, read from its usage listing.

    install-plist.sh with no arguments exits 2 and prints `labels available (from
    <source>)` followed by one indented label per line. Parsing that keeps this
    check and the installer on one enumerator: a template the installer cannot
    reach must not read as covered here.
    """
    r = subprocess.run(["bash", str(INSTALLER)], capture_output=True, text=True,
                       timeout=120)
    text = r.stdout + r.stderr
    if "labels available" not in text:
        raise SystemExit("could not read the installer's label listing; it printed:\n"
                         + text[:1000])
    labels = re.findall(r"^\s+(com\.kipi\.[A-Za-z0-9_.-]+)\s*$", text, re.M)
    if not labels:
        raise SystemExit("the installer listed no labels at all, which is a defect "
                         "in the enumerator, not a clean population")
    return sorted(set(labels))


def main():
    loaded = loaded_labels()
    if loaded is None:
        print("SKIP no launchctl on this host, so there is no loaded-label "
              "population to check. This says nothing about the founder's "
              "machine; it says this host cannot answer the question.")
        return 0
    committed = committed_labels()
    missing = [l for l in loaded if l not in committed]
    unexplained = [l for l in missing if l not in ALLOWLIST]

    print("loaded %s labels ........ %d" % (PREFIX, len(loaded)))
    print("committed templates ..... %d" % len(committed))
    print("loaded with no template .. %d" % len(missing))
    for label in missing:
        note = ALLOWLIST.get(label)
        print("    %s  %s" % (label, "ALLOWLISTED" if note else "UNEXPLAINED"))
        if note:
            print("        %s" % note)

    # A STALE ENTRY WARNS, IT DOES NOT FAIL. com.kipi.pr86-review is built to
    # unload itself when PR #86 closes, so failing on "allowlisted but no longer
    # loaded" would turn this gate red on the good outcome. A gate that goes red
    # when the problem resolves is a gate that gets switched off.
    for label, note in sorted(ALLOWLIST.items()):
        if label not in loaded:
            print("NOTE stale allowlist entry: %s is no longer loaded, the entry "
                  "can be deleted" % label)
        elif label in committed:
            print("NOTE stale allowlist entry: %s now HAS a committed template, "
                  "the entry can be deleted" % label)

    if unexplained:
        print("FAIL loaded with no committed template and no allowlist entry: %s"
              % ", ".join(unexplained), file=sys.stderr)
        print("     Commit a template (q-system/.q-system/scripts/<label>.plist) "
              "or add a dated ALLOWLIST entry saying why not.", file=sys.stderr)
        return 1
    print("ok   every loaded %s label has a committed template or a dated exemption"
          % PREFIX)
    return 0


if __name__ == "__main__":
    sys.exit(main())
