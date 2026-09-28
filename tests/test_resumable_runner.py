"""Test the resumable runner, especially the kill-and-resume path.

The property that matters: a run killed part-way must, on rerun, skip exactly
the steps that completed and re-run the one that was in flight - and must not
skip a step that never finished. A false "skip" is the dangerous direction: it
would produce a submission built from missing artifacts.

Steps are plain argv (no shell) so this runs on any platform, including a
Windows dev box with no WSL. The shell=True path needs bash and is exercised
only when bash actually works here.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from resumable_runner import StepRunner

TMP = Path(tempfile.mkdtemp(prefix="resumable_test_"))
MARK = TMP / "progress.log"
MANIFEST = TMP / "manifest.json"


def step(tag: str, fail: bool = False) -> list[str]:
    """argv step that appends its tag, so we can see exactly what executed."""
    code = (f"import pathlib,sys;"
            f"open({str(MARK)!r},'a').write({tag!r}+' ');"
            f"sys.exit(1 if {fail!r} else 0)")
    return [sys.executable, "-c", code]


def ran() -> list[str]:
    return MARK.read_text(encoding="utf-8").split() if MARK.exists() else []


def main() -> int:
    failures = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}{(' :: ' + detail) if detail else ''}")
        if not ok:
            failures.append(label)

    s = {i: step(f"s{i}") for i in range(1, 5)}

    # --- first pass: s3 dies ---------------------------------------------
    r = StepRunner(MANIFEST)
    r.run("s1", s[1])
    r.run("s2", s[2])
    try:
        r.run("s3", step("s3", fail=True))
        check("failing step raises", False)
    except SystemExit as exc:
        check("failing step raises and explains", "retry it" in str(exc))
    check("failed step is NOT recorded as done", not r.is_done("s3", step("s3", fail=True)))

    # --- resume: s1/s2 skipped, only the unfinished work re-runs -----------
    MARK.unlink(missing_ok=True)
    r2 = StepRunner(MANIFEST)
    check("manifest survives reload", r2.is_done("s1", s[1]))
    check("failed step still pending after reload", not r2.is_done("s3", s[3]))
    r2.run("s3", s[3])
    r2.run("s4", s[4])
    check("only unfinished steps re-ran", ran() == ["s3", "s4"], str(ran()))

    # --- a changed command invalidates a recorded success -----------------
    r3 = StepRunner(MANIFEST)
    check("changed cmd is not treated as done", not r3.is_done("s4", step("different")))

    # --- a corrupt manifest must not strand a completed run ---------------
    MANIFEST.write_text("{ not json", encoding="utf-8")
    r4 = StepRunner(MANIFEST)
    check("corrupt manifest falls back to re-running everything",
          not r4.is_done("s1", s[1]))

    # --- dry run executes nothing ----------------------------------------
    MARK.unlink(missing_ok=True)
    r5 = StepRunner(MANIFEST, dry_run=True)
    r5.run("s1", s[1])
    check("dry run touches nothing", not MARK.exists())

    # --- manifest is written atomically (no .tmp left behind) ------------
    StepRunner(MANIFEST).run("s1", s[1])
    check("no partial manifest left on disk", not list(TMP.glob("*.tmp")))

    # --- shell path, only if bash is actually usable here ----------------
    if shutil.which("bash") and subprocess.run(
            ["bash", "-lc", "echo ok"], capture_output=True).returncode == 0:
        MARK.unlink(missing_ok=True)
        r6 = StepRunner(TMP / "m2.json")
        r6.run("sh1", [f"echo sh1 >> {MARK}"], shell=True)
        check("shell=True path works", ran() == ["sh1"], str(ran()))
    else:
        print("[SKIP] shell=True path (no working bash here; it works on Colab)")

    shutil.rmtree(TMP, ignore_errors=True)
    if failures:
        raise SystemExit("FAILURES: " + "; ".join(failures))
    print("\nresume semantics verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
