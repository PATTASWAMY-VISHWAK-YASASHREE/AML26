"""Resumable step runner for an existing pipeline defined as a list of steps.

A 3-4 hour pipeline on free Colab is regularly killed by session pre-emption, and
if every step overwrites its own outputs then a kill at hour 3 means restarting
from zero. This wraps an arbitrary step list in a manifest-based resume:

  - a step is recorded as done ONLY after it exits 0, so a step killed
    mid-flight is always re-run and never trusted;
  - a crash therefore re-runs at most the one step that was in progress;
  - `--only` / `--from` let you re-run a single step or resume from one.

Deliberately does NOT try to guess each step's output artifacts: an incorrect
sentinel name would silently skip a step that never ran, which is far worse than
re-running one. The exit code is the only signal used.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


class StepRunner:
    def __init__(self, manifest: Path, dry_run: bool = False) -> None:
        self.manifest = manifest
        self.dry_run = dry_run
        self.done: dict[str, dict] = {}
        if manifest.exists():
            try:
                self.done = json.loads(manifest.read_text(encoding="utf-8")).get("steps", {})
            except (OSError, ValueError):
                # A truncated manifest must not strand a completed run: start over
                # rather than trust partial state.
                self.done = {}
        self.manifest.parent.mkdir(parents=True, exist_ok=True)

    def _save(self) -> None:
        tmp = self.manifest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"steps": self.done}, indent=2), encoding="utf-8")
        tmp.replace(self.manifest)  # atomic: never leave a half-written manifest

    def is_done(self, name: str, cmd: list[str], cwd: str | None = None) -> bool:
        rec = self.done.get(name)
        if not rec:
            return False
        # If the command or working directory changed, the recorded success no
        # longer applies - the step must run again.
        if rec.get("cmd") != cmd or rec.get("cwd") != cwd:
            return False
        return bool(rec.get("ok"))

    def run(self, name: str, cmd: list[str], cwd: str | None = None,
            env: dict | None = None, allow_fail: bool = False,
            shell: bool = False) -> int:
        """Run one step.

        By default `cmd` is an argv list executed directly - no shell, so no
        quoting or redirection surprises. Pass shell=True for a real command
        line (redirection, pipes, `&&`); that path needs bash and therefore
        Linux/macOS or a working WSL.
        """
        if shell:
            full = ["bash", "-lc", " ".join(cmd)]
        else:
            full = list(cmd)
        if self.dry_run:
            print(f"  [dry-run] {name}: {full}")
            return 0
        print(f"\n>>> {name}\n    {' '.join(full)}", flush=True)
        t0 = time.time()
        import os as _os
        environ = {**_os.environ, **(env or {})}
        proc = subprocess.run(full, cwd=cwd, env=environ)
        dt = time.time() - t0
        ok = proc.returncode == 0
        print(f"<<< {name}: exit {proc.returncode} in {dt:.0f}s", flush=True)
        self.done[name] = {"cmd": cmd, "cwd": cwd, "ok": ok,
                           "seconds": round(dt, 1),
                           "finished": time.strftime("%Y-%m-%d %H:%M:%S")}
        self._save()
        if not ok and not allow_fail:
            raise SystemExit(
                f"step {name!r} failed (exit {proc.returncode}); it stays unmarked so "
                f"a rerun will retry it. Re-run the same cell to resume.")
        return proc.returncode


def pending(runner: StepRunner, steps: list) -> list:
    return [s for s in steps if not runner.is_done(s["name"], s["cmd"], s.get("cwd"))]
