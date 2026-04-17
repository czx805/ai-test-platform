# -*- coding: utf-8 -*-
"""
auto_sync.py -- test pass + auto git push to GitHub

Usage:
    python auto_sync.py            # run tests, push if all pass
    python auto_sync.py --dry-run  # show git status only, no test/push
"""
import subprocess
import sys
import os
import json
import re
import datetime

# Fix Windows GBK stdout encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
if sys.stderr.encoding != "utf-8":
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

REPO_DIR     = r"D:\aitest\wukong\ai-test-platform"
VENV_PY      = os.path.join(REPO_DIR, "venvs", "Scripts", "python.exe")
REPORTS_JSON = os.path.join(REPO_DIR, "reports", "report_data.json")
LOG_FILE     = os.path.join(REPO_DIR, "reports", "sync.log")


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(cmd, cwd=None, capture=True):
    kwargs = {"cwd": cwd or REPO_DIR, "shell": True}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    r = subprocess.run(cmd, **kwargs)
    return r.returncode, (r.stdout or b"").decode("utf-8", errors="replace"), (r.stderr or b"").decode("utf-8", errors="replace")


def git_status():
    rc, out, _ = run("git status --porcelain")
    lines = [l for l in out.strip().splitlines() if l.strip()]
    return bool(lines), lines


def git_has_remote():
    rc, out, _ = run("git remote -v")
    return "origin" in out


def git_last_sha():
    rc, out, _ = run("git rev-parse --short HEAD")
    return out.strip()


def run_tests():
    # clean old report
    if os.path.exists(REPORTS_JSON):
        os.remove(REPORTS_JSON)

    log("=" * 60)
    log("RUN pytest ...")
    log("=" * 60)

    py = VENV_PY if os.path.exists(VENV_PY) else sys.executable
    rc, out, err = run(f'"{py}" -m pytest tests/ -v --tb=short 2>&1')

    # print output to console
    print(out)
    if err.strip():
        print(err)

    log(f"pytest exit code = {rc}")

    passed = failed = total = 0
    if os.path.exists(REPORTS_JSON):
        try:
            with open(REPORTS_JSON, encoding="utf-8") as f:
                data = json.load(f)
            passed = data.get("passed", 0)
            failed = data.get("failed", 0)
            total  = data.get("total",  0)
            log(f"report: {passed} pass / {failed} fail / {total} total")
        except Exception as e:
            log(f"report parse error: {e}")

    return passed, failed, total


def do_sync():
    now = datetime.datetime.now()

    if not git_has_remote():
        log("WARN: no remote origin, skip push")
        return False

    # git add
    rc, _, err = run("git add -A")
    if rc != 0:
        log(f"ERROR: git add failed: {err}")
        return False

    dirty, lines = git_status()
    if not dirty:
        log("CLEAN: nothing to commit")
        return True

    # list changed files
    changed = sorted(set(
        re.sub(r"^[ A-Z?]+", "", l).strip()
        for l in lines
        if re.sub(r"^[ A-Z?]+", "", l).strip()
    ))
    log(f"Changed files ({len(changed)}): " + ", ".join(changed))

    passed = failed = total = 0
    if os.path.exists(REPORTS_JSON):
        try:
            with open(REPORTS_JSON, encoding="utf-8") as f:
                data = json.load(f)
            passed = data.get("passed", 0)
            failed = data.get("failed", 0)
            total  = data.get("total",  0)
        except Exception:
            pass

    # commit message
    if failed == 0 and total > 0:
        msg = f"auto-sync: {passed}/{total} pass @ {now:%Y-%m-%d %H:%M}"
    else:
        msg = f"auto-sync @ {now:%Y-%m-%d %H:%M}"

    log(f"COMMIT: {msg}")
    rc, _, err = run(f"git commit -m {repr(msg)}")
    if rc != 0:
        log(f"ERROR: git commit failed: {err}")
        return False

    log("PUSH to GitHub ...")
    rc, out, err = run("git push")
    if rc != 0:
        log(f"ERROR: git push failed: {err}")
        return False

    sha = git_last_sha()
    log(f"OK: pushed commit {sha}")
    return True


def main():
    dry_run = "--dry-run" in sys.argv

    print(f"[{'DRY RUN' if dry_run else 'LIVE'}] auto_sync.py  |  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"Repo: {REPO_DIR}")

    # git status check
    dirty, lines = git_status()
    if dirty:
        print(f"GIT: {len(lines)} change(s) detected")
        for l in lines:
            print(f"  {l}")
    else:
        print("GIT: clean (no changes)")

    if dry_run:
        print("DRY RUN: exit, no test, no push")
        return

    # run tests
    passed, failed, total = run_tests()
    print(f"RESULT: {passed} pass / {failed} fail / {total} total")

    if total == 0:
        log("WARN: no test collected, skip sync")
        return

    if failed > 0:
        log(f"FAIL: {failed} case(s) failed, skip push")
        return

    if passed > 0 and failed == 0:
        log("PASS: all green, sync now ...")
        ok = do_sync()
        if ok:
            log("DONE")
        else:
            log("SYNC FAILED")
    else:
        log(f"UNKNOWN state passed={passed} failed={failed}")


if __name__ == "__main__":
    main()
