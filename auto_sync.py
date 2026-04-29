# -*- coding: utf-8 -*-
"""
auto_sync.py -- AI测试平台自动同步脚本

功能：
  1. 运行 pytest 测试
  2. 成功后推送到 GitHub
  3. 所有情况（成功/失败/超时）都发钉钉通知
"""
import subprocess, sys, os, json, re, datetime, hmac, hashlib, base64, urllib.parse, urllib.request, time, threading

# Fix Windows GBK stdout
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
if sys.stderr.encoding != "utf-8":
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

REPO_DIR     = r"D:\aitest\wukong\ai-test-platform"
VENV_PY      = os.path.join(REPO_DIR, "venvs", "Scripts", "python.exe")
REPORTS_JSON = os.path.join(REPO_DIR, "reports", "report_data.json")
LOG_FILE     = os.path.join(REPO_DIR, "reports", "sync.log")

DINGTALK_TOKEN = "62bc5ff38f7b6a10421c698a27a3ee0f5623feeb85f8c200c3bead3e56e2450a"
DINGTALK_SECRET = "SEC004404742933dbe064b38b315ee25084ccede761f6a4e847e61e15d60ae5dc68"


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(cmd, cwd=None, timeout=None):
    kwargs = {"cwd": cwd or REPO_DIR, "shell": True, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if timeout:
        kwargs["timeout"] = timeout
    try:
        r = subprocess.run(cmd, **kwargs)
        return r.returncode, (r.stdout or b"").decode("utf-8", errors="replace"), (r.stderr or b"").decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", errors="replace")
        err = (e.stderr or b"").decode("utf-8", errors="replace")
        return -1, out, err


def parse_pytest_output(out):
    """从 pytest -v 输出中解析 passed/failed/total"""
    passed = failed = total = 0
    # 统计每一行的 PASSED/FAILED 标记
    for line in out.splitlines():
        # 匹配 [gwX] [ YY%] PASSED tests/... 或 [gwX] [ YY%] FAILED tests/...
        if re.search(r"\[gw\d+\]\s*\[\s*\d+%\]\s*PASSED", line):
            passed += 1
        elif re.search(r"\[gw\d+\]\s*\[\s*\d+%\]\s*FAILED", line):
            failed += 1
    total = passed + failed
    # 如果上面没匹配到，尝试摘要行
    if total == 0:
        summary_match = re.search(r"(\d+) passed", out)
        if summary_match:
            passed = int(summary_match.group(1))
        summary_match2 = re.search(r"(\d+) failed", out)
        if summary_match2:
            failed = int(summary_match2.group(1))
        total = passed + failed
    # 也看 collected 行
    if total == 0:
        m = re.search(r"(\d+) selected", out)
        if m:
            total = int(m.group(1))
    return passed, failed, total


def run_pytest(timeout=1200):
    """
    运行 pytest，支持硬超时（超时后强制 kill 并发通知）
    返回: (rc, out, killed_flag)
    """
    log(f"[run_pytest] timeout={timeout}s")

    py = VENV_PY if os.path.exists(VENV_PY) else sys.executable
    cmd = f'"{py}" -m pytest tests/ -v --tb=short --timeout=120 -n 3 --dist=loadscope'
    log(f"[run_pytest] cmd: {cmd}")

    proc = subprocess.Popen(
        cmd, cwd=REPO_DIR, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", bufsize=1,
    )

    lines = []
    killed = [False]
    timer_active = [True]

    def _read():
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
            log(f"[run_pytest] TIMEOUT after {timeout}s -- killing process")
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            except Exception as e:
                log(f"[run_pytest] kill error: {e}")

    threading.Thread(target=_read, daemon=True).start()
    threading.Thread(target=_kill_after_timeout, daemon=True).start()

    proc.wait()
    timer_active[0] = False
    out = "".join(lines)

    log(f"[run_pytest] rc={proc.returncode}, killed={killed[0]}")
    return proc.returncode, out, killed[0]


def send_dingtalk(title, text):
    try:
        ts = str(int(time.time() * 1000))
        sign_str = f"{ts}\n{DINGTALK_SECRET}"
        sign = urllib.parse.quote_plus(base64.b64encode(
            hmac.new(DINGTALK_SECRET.encode(), sign_str.encode(), hashlib.sha256).digest()
        ))
        url = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}&timestamp={ts}&sign={sign}"
        data = json.dumps({
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
            "at": {"isAtAll": False},
        }).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
        ok = result.get("errcode") == 0
        log(f"DingTalk: {'OK' if ok else 'FAILED'} - {result}")
        return ok
    except Exception as e:
        log(f"DingTalk error: {e}")
        return False


def git_has_remote():
    rc, out, _ = run("git remote -v")
    return "origin" in out


def git_status_lines():
    rc, out, _ = run("git status --porcelain")
    return [l for l in out.strip().splitlines() if l.strip()]


def git_last_sha():
    rc, out, _ = run("git rev-parse --short HEAD")
    return out.strip()


def git_add_and_commit(msg):
    run("git add -A")
    safe_msg = msg.replace('"', '\\"')
    rc, _, err = run(f'git commit -m "{safe_msg}"')
    if rc != 0:
        log(f"git commit failed: {err}")
        return False
    return True


def git_push(retry=1):
    for i in range(retry + 1):
        rc, out, err = run("git push")
        if rc == 0:
            return True
        log(f"git push failed (attempt {i+1}): {err}")
        if i < retry:
            time.sleep(5)
    return False


def build_fail_detail(out, max_cases=5, max_msg_len=200):
    """从 pytest 输出中提取失败用例详情"""
    blocks = []
    # 找每个 FAILED 块
    for chunk in re.split(r"(?=FAILED\s)", out):
        if not chunk.strip():
            continue
        lines = chunk.splitlines()
        if not lines:
            continue
        # 第一行是 test id
        title_line = lines[0].strip()
        # 提取 assertion message
        msg_lines = []
        for ln in lines[1:]:
            if re.match(r"(FAILED|PASSED|SHORT|ERROR|___)", ln):
                break
            ln = ln.strip()
            if ln and not ln.startswith("="):
                msg_lines.append(ln)
        msg = " ".join(msg_lines).strip()
        if len(msg) > max_msg_len:
            msg = msg[:max_msg_len] + "..."
        blocks.append((title_line, msg))
    return blocks[:max_cases]


def send_report(passed, failed, total, out, killed=False, extra_msg=""):
    """发送钉钉报告"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if killed:
        status_emoji = "⏱"
        status_text = "pytest 超时终止"
        # 取最后 30 行作为失败上下文
        last_lines = out.splitlines()[-30:]
        # 找最后一个 "正在运行" 的测试
        running_test = ""
        for ln in reversed(last_lines):
            m = re.search(r"(tests?[/\\][\w_]+\.py::[\w_]+)", ln)
            if m:
                running_test = m.group(1)
                break
        footer = f"\n\n> **超时原因**: pytest 运行超过 20 分钟未完成"
        if running_test:
            footer += f"\n> **最后运行**: `{running_test}` 疑似卡住"
        footer += f"\n\n```\n" + "\n".join(last_lines) + "\n```"
    elif failed > 0:
        status_emoji = "❌"
        status_text = f"{failed} 个失败"
        fail_cases = build_fail_detail(out)
        footer = "\n\n---\n\n### 失败用例\n\n"
        for i, (title, msg) in enumerate(fail_cases, 1):
            footer += f"**{i}. {title}**\n\n"
            if msg:
                footer += f"> {msg}\n\n"
        footer += f"\n> 完整日志：`reports/sync.log`"
    elif total == 0:
        status_emoji = "⚠️"
        status_text = "无测试用例"
        footer = f"\n> pytest 未收集到任何测试用例"
    else:
        status_emoji = "✅"
        status_text = "全部通过"
        footer = ""

    text = (
        f"## {status_emoji} AI测试平台 - 自动测试报告\n\n"
        f"- **时间**: {now_str}\n"
        f"- **状态**: {status_text}\n"
        f"- **通过**: {passed} / **失败**: {failed} / **总计**: {total}\n"
        f"- **触发**: 自动定时任务\n"
    )
    if extra_msg:
        text += f"\n{extra_msg}"
    text += footer

    send_dingtalk(f"AI测试平台 - {status_text}", text)


def main():
    dry_run = "--dry-run" in sys.argv
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{'DRY RUN' if dry_run else 'LIVE'}] auto_sync.py  |  {now_str}")

    if dry_run:
        lines = git_status_lines()
        print(f"GIT: {'dirty (' + str(len(lines)) + ' changes)' if lines else 'clean'}")
        return

    # clean old report
    if os.path.exists(REPORTS_JSON):
        os.remove(REPORTS_JSON)

    log("=" * 60)
    log("START pytest")
    log("=" * 60)

    # 运行 pytest（20分钟超时）
    rc, out, killed = run_pytest(timeout=1200)
    log(f"pytest done: rc={rc}, killed={killed}")

    # 解析结果
    passed, failed, total = parse_pytest_output(out)

    # 保存输出到 log
    log_path = os.path.join(REPO_DIR, "reports", "pytest_output.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(out)

    # 超时情况：立即发通知（不走 git push）
    if killed:
        log("RESULT: TIMEOUT -- sending notification immediately")
        send_report(passed, failed, total, out, killed=True)
        return

    # 打印结果
    print(f"RESULT: {passed} pass / {failed} fail / {total} total")

    # 失败情况：发通知，不 push
    if failed > 0:
        log(f"RESULT: {failed} failures -- notify and skip push")
        send_report(passed, failed, total, out)
        return

    # 无测试用例
    if total == 0:
        log("RESULT: no tests collected")
        send_report(passed, failed, total, out)
        return

    # 全部通过：push
    if not git_has_remote():
        log("WARN: no remote -- notify but skip push")
        send_report(passed, failed, total, out, extra_msg="> **注意**: 仓库无 remote，不推送")
        return

    dirty = git_status_lines()
    if not dirty:
        log("CLEAN: nothing to commit -- notify")
        send_report(passed, failed, total, out, extra_msg="> **Git**: 无代码变更")
        return

    # 有变更 → commit + push
    now = datetime.datetime.now()
    msg = f"auto-sync: {passed}/{total} pass @ {now:%Y-%m-%d %H:%M}"
    if not git_add_and_commit(msg):
        send_report(passed, failed, total, out, extra_msg="> **Git**: commit 失败")
        return

    sha = git_last_sha()
    ok = git_push(retry=1)
    if ok:
        send_report(passed, failed, total, out,
                    extra_msg=f"> **Git Push**: 成功 (`{sha}`)")
    else:
        send_report(passed, failed, total, out,
                    extra_msg=f"> **Git Push**: 失败（commit 已保存本地）")


if __name__ == "__main__":
    main()
