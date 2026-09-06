#!/usr/bin/env python3
"""auto-commit.py commits nothing while the fleet updater's run marker is live.

On 2026-09-06 the consulting checkout's Stop-hook auto-commit fired at every
peer message while kipi-update.sh was mid-delivery, committed the updater's
rules, settings and plugins under its own generic messages, and held
index.lock through its 445 s verify so the founder's guarded re-run tripped
and did nothing (sp-9306036e). The updater now writes
<git-common-dir>/kipi-update.run for the duration of one instance apply; this
pins the hook's half of the handshake:

  live marker  (pid alive)  -> exit 0, one stderr line, no commit, marker kept
  stale marker (pid dead)   -> marker removed, hook proceeds as before
  no marker                 -> unchanged behaviour

Runs against a throwaway repo only; never the checkout it lives in.
"""
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "auto-commit.py")


def git(repo, *args):
    return subprocess.run(
        ["git", "-c", "user.email=t@t.t", "-c", "user.name=test",
         "-c", "commit.gpgsign=false", *args],
        cwd=repo, capture_output=True, text=True, check=False)


def run_hook(repo):
    return subprocess.run([sys.executable, HOOK], cwd=repo,
                          capture_output=True, text=True, check=False)


def head_count(repo):
    return int(git(repo, "rev-list", "--count", "HEAD").stdout.strip() or 0)


def dead_pid():
    child = subprocess.Popen(["true"])
    child.wait()
    return child.pid


class RunMarker(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="auto-commit-marker-")
        git(self.repo, "init", "-q", "-b", "main")
        # A path the hook classifies as committable, so the "no marker" and
        # "stale marker" cases have something to commit and the live case has
        # something it must NOT commit.
        os.makedirs(os.path.join(self.repo, "q-system", "memory"))
        with open(os.path.join(self.repo, "q-system", "memory", "last-handoff.md"), "w") as fh:
            fh.write("v1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "init")
        with open(os.path.join(self.repo, "q-system", "memory", "last-handoff.md"), "w") as fh:
            fh.write("v2\n")
        self.marker = os.path.join(self.repo, ".git", "kipi-update.run")

    def test_live_marker_commits_nothing_and_says_so(self):
        with open(self.marker, "w") as fh:
            fh.write(f"{os.getpid()} 2026-09-06T21:30:00Z\n")
        before = head_count(self.repo)
        result = run_hook(self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fleet updater run in progress", result.stderr)
        self.assertEqual(head_count(self.repo), before, "the hook committed under a live marker")
        self.assertTrue(os.path.exists(self.marker), "the hook removed a LIVE marker")

    def test_stale_marker_is_removed_and_the_hook_proceeds(self):
        with open(self.marker, "w") as fh:
            fh.write(f"{dead_pid()} 2026-09-06T21:30:00Z\n")
        result = run_hook(self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("fleet updater run in progress", result.stderr)
        self.assertFalse(os.path.exists(self.marker), "a stale marker survived")

    def test_malformed_marker_is_treated_as_stale(self):
        with open(self.marker, "w") as fh:
            fh.write("not-a-pid\n")
        result = run_hook(self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("fleet updater run in progress", result.stderr)
        self.assertFalse(os.path.exists(self.marker))

    def test_no_marker_is_the_old_behaviour(self):
        before = head_count(self.repo)
        result = run_hook(self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("fleet updater run in progress", result.stderr)
        # The floor that makes the live case meaningful: without a marker the
        # same dirty file DOES get committed, so "no commit" above is the marker's
        # doing and not the classifier's.
        self.assertEqual(head_count(self.repo), before + 1,
                         f"control failed: the hook did not commit without a marker: {result.stdout} {result.stderr}")


if __name__ == "__main__":
    unittest.main()
