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
import hmac
import hashlib
import base64
import urllib.parse
import urllib.request
import time

# Fix Windows GBK stdout encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
if sys.stderr.encoding != "utf-8":
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

REPO_DIR     = r"D:\aitest\wukong\ai-test-platform"
VENV_PY      = os.path.join(REPO_DIR, "venvs", "Scripts", "python.exe")
REPORTS_JSON = os.path.join(REPO_DIR, "reports", "report_data.json")
LOG_FILE     = os.path.join(REPO_DIR, "reports", "sync.log")

# DingTalk webhook config
DINGTALK_ACCESS_TOKEN = "62bc5ff38f7b6a10421c698a27a3ee0f5623feeb85f8c200c3bead3e56e2450a"
DINGTALK_SECRET       = "SEC004404742933dbe064b38b315ee25084ccede761f6a4e847e61e15d60ae5dc68"


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(cmd, cwd=None, capture=True, timeout=None):
    kwargs = {"cwd": cwd or REPO_DIR, "shell": True}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    if timeout:
        kwargs["timeout"] = timeout
    try:
        r = subprocess.run(cmd, **kwargs)
    except subprocess.TimeoutExpired as e:
        log(f"TIMEOUT: process killed after {timeout}s")
        out = (e.stdout or b"").decode("utf-8", errors="replace")
        err = (e.stderr or b"").decode("utf-8", errors="replace")
        return -1, out, err
    return r.returncode, (r.stdout or b"").decode("utf-8", errors="replace"), (r.stderr or b"").decode("utf-8", errors="replace")


def run_pytest(cmd, timeout=600):
    """
    运行 pytest 并在超时后强制杀进程树。
    使用 Popen + 外部计时器，避免 Playwright teardown 无限卡死导致 subprocess.run() 永久阻塞。
    """
    import threading, time, signal

    log(f"[run_pytest] cmd: {cmd}")
    log(f"[run_pytest] timeout: {timeout}s")

    proc = subprocess.Popen(
        cmd,
        cwd=REPO_DIR,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )

    lines = []
    timer_active = [True]   # 用 list 方便在嵌套函数中修改
    killed = [False]

    def _read_stdout():
        try:
            for line in iter(proc.stdout.readline, ""):
                if line:
                    lines.append(line)
                    print(line, end="", flush=True)
        except Exception:
            pass

    def _kill_after_timeout():
        time.sleep(timeout)
        if timer_active[0] and proc.poll() is None:
            killed[0] = True
            log(f"[run_pytest] HARD TIMEOUT after {timeout}s — killing process tree")
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                    )
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception as e:
                log(f"[run_pytest] kill error: {e}")

    reader = threading.Thread(target=_read_stdout, daemon=True)
    killer = threading.Thread(target=_kill_after_timeout, daemon=True)
    reader.start()
    killer.start()

    proc.wait()
    timer_active[0] = False
    reader.join(timeout=5)
    killer.join(timeout=1)

    out = "".join(lines)
    rc = proc.returncode

    if killed[0]:
        log(f"[run_pytest] Killed by timeout (rc={rc})")
        return -1, out, ""
    else:
        log(f"[run_pytest] Exit code: {rc}")
        return rc, out, ""


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


def send_dingtalk(title, text, at_all=False):
    """Send markdown message to DingTalk group robot."""
    try:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{DINGTALK_SECRET}"
        hmac_code = hmac.new(
            DINGTALK_SECRET.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = (
            f"https://oapi.dingtalk.com/robot/send"
            f"?access_token={DINGTALK_ACCESS_TOKEN}"
            f"&timestamp={timestamp}&sign={sign}"
        )
        data = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
            "at": {"isAtAll": at_all},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode("utf-8"))
        if result.get("errcode") == 0:
            log("DingTalk: message sent OK")
        else:
            log(f"DingTalk: send failed - {result}")
        return result
    except Exception as e:
        log(f"DingTalk: send error - {e}")
        return None


def run_tests():
    # clean old report
    if os.path.exists(REPORTS_JSON):
        os.remove(REPORTS_JSON)

    log("=" * 60)
    log("RUN pytest ...")
    log("=" * 60)

    py = VENV_PY if os.path.exists(VENV_PY) else sys.executable
    cmd = f'"{py}" -m pytest tests/ -v --tb=short --timeout=120'
    rc, out, err = run_pytest(cmd, timeout=3600)

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
    # 用双引号包裹 commit message，内部双引号转义
    safe_msg = msg.replace('"', '\\"')
    rc, _, err = run(f'git commit -m "{safe_msg}"')
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
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"[{'DRY RUN' if dry_run else 'LIVE'}] auto_sync.py  |  {now_str}")
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

    # build DingTalk notification
    if failed == 0 and total > 0:
        status_emoji = "✅"
        status_text = "全部通过"
    elif failed > 0:
        status_emoji = "❌"
        status_text = f"{failed} 个失败"
    else:
        status_emoji = "⚠️"
        status_text = "无测试用例"

    dingtalk_text = (
        f"## {status_emoji} AI测试平台 - 自动测试报告\n\n"
        f"- **时间**: {now_str}\n"
        f"- **结果**: {status_text}\n"
        f"- **通过**: {passed} / **失败**: {failed} / **总计**: {total}\n"
    )

    # 失败用例详情
    if failed > 0 and os.path.exists(REPORTS_JSON):
        try:
            with open(REPORTS_JSON, encoding="utf-8") as f:
                report = json.load(f)
            fail_cases = [t for t in report.get("tests", []) if t.get("outcome") == "failed"]
            if fail_cases:
                dingtalk_text += "\n---\n\n### ❌ 失败用例详情\n\n"
                for i, t in enumerate(fail_cases, 1):
                    name = t.get("title") or t.get("nodeid", "unknown")
                    dur = t.get("duration", 0)
                    msg = t.get("failure_msg", "").strip()
                    # 截断过长的错误信息（钉钉 markdown 限制）
                    if len(msg) > 300:
                        msg = msg[:300] + "…"
                    dingtalk_text += f"**{i}. {name}** ({dur:.1f}s)\n\n"
                    if msg:
                        dingtalk_text += f"> {msg}\n\n"
        except Exception as e:
            log(f"report parse error (fail detail): {e}")

    if total == 0:
        log("WARN: no test collected, skip sync")
        send_dingtalk("AI测试平台 - 测试报告", dingtalk_text)
        return

    if failed > 0:
        log(f"FAIL: {failed} case(s) failed, skip push")
        send_dingtalk("AI测试平台 - 测试报告", dingtalk_text)
        return

    if passed > 0 and failed == 0:
        log("PASS: all green, sync now ...")
        ok = do_sync()
        sha = git_last_sha()
        if ok:
            log("DONE")
            dingtalk_text += f"\n- **Git Push**: 成功 (commit `{sha}`)\n"
            send_dingtalk("AI测试平台 - 测试报告", dingtalk_text)
        else:
            log("SYNC FAILED")
            dingtalk_text += f"\n- **Git Push**: 失败\n"
            send_dingtalk("AI测试平台 - 测试报告", dingtalk_text)
    else:
        log(f"UNKNOWN state passed={passed} failed={failed}")
        send_dingtalk("AI测试平台 - 测试报告", dingtalk_text)


if __name__ == "__main__":
    main()
