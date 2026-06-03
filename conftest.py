# -*- coding: utf-8 -*-
"""
conftest.py — pytest fixtures
提供浏览器、页面等共享资源，支持所有测试用例。

策略：
- 登录测试（test_login）：function scope，每个用例独立 context + page，保证隔离
- 工作台测试（test_workbench）：module scope 共享已登录 context，避免重复登录

报告收集：支持 pytest-xdist 并行运行，使用文件锁合并各 worker 结果
"""
import atexit
import json
import os
import time
import tempfile
from datetime import datetime
import pytest
from playwright.sync_api import sync_playwright

# ── 自定义报告钩子：收集结果写 JSON（支持 xdist 并行）────────────────
import time as _time

_test_results = []        # list[dict] - 当前 worker 的结果
_session_start = None     # session 开始时间

# ── atexit 延迟清理：解决 Playwright teardown hang ──────────────
#
# 问题根因：fixture teardown 里直接调用 page.close() / ctx.close() /
# browser.close()，在 pytest-timeout 超时或 SIGKILL 时，C 扩展线程
# 的 close() 调用无法被中断，导致后续所有测试的 Playwright 操作卡死。
#
# 解决方案：teardown 时只记录对象引用，在进程退出时才关闭（atexit）。
# Python atexit handler 在 SIGTERM/SIGINT 之后执行，不受 pytest 超时影响，
# 且只在进程真正退出前运行一次，彻底避免 teardown hang。

_teardown_scheduled = False


def _schedule_teardown():
    global _teardown_scheduled
    if _teardown_scheduled:
        return
    _teardown_scheduled = True

    def _cleanup_all():
        # 逆序清理：pages → contexts → browser
        # 注意：browser.close() 会自动关闭所有子 context，
        # 所以清理顺序不影响最终结果，这里只是做兜底。
        while _playwright_pages:
            p = _playwright_pages.pop()
            try:
                p.close()
            except Exception:
                pass
        while _playwright_contexts:
            c = _playwright_contexts.pop()
            try:
                c.close()
            except Exception:
                pass
        if _playwright_instance:
            try:
                _playwright_instance.stop()
            except Exception:
                pass

    atexit.register(_cleanup_all)


_playwright_instance = None
_playwright_pages     = []
_playwright_contexts = []


def _get_worker_id():
    """获取 xdist worker ID，如果没有则返回 'master'"""
    return os.environ.get("PYTEST_XDIST_WORKER", "master")


def _get_result_file():
    """获取当前 worker 的结果临时文件路径"""
    worker_id = _get_worker_id()
    report_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(report_dir, exist_ok=True)
    return os.path.join(report_dir, f"_test_results_{worker_id}.json")


def _save_worker_results():
    """保存当前 worker 的结果到临时文件"""
    result_file = _get_result_file()
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(_test_results, f, ensure_ascii=False, indent=2)


def _merge_all_worker_results():
    """合并所有 worker 的结果文件"""
    report_dir = os.path.join(os.path.dirname(__file__), "reports")
    all_results = []
    
    # 查找所有 worker 结果文件
    for fname in os.listdir(report_dir):
        if fname.startswith("_test_results_") and fname.endswith(".json"):
            fpath = os.path.join(report_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    worker_results = json.load(f)
                    all_results.extend(worker_results)
            except Exception:
                pass
            # 删除临时文件
            try:
                os.remove(fpath)
            except Exception:
                pass
    
    return all_results


def pytest_configure(config):
    pass  # no-op


def pytest_sessionstart(session):
    global _session_start
    _session_start = _time.time()


def pytest_runtest_logreport(report):
    """收集每个测试用例的运行时信息（只在 worker 进程中记录，避免 xdist 重复）"""
    worker_id = _get_worker_id()
    # xdist 使用时，master 进程也会收到 hook，跳过它（只在 worker 中记录）
    if worker_id == "master" and "PYTEST_XDIST_WORKER_COUNT" in os.environ:
        return
    if report.when == "call":
        # 截图路径（每个用例的截图放在 logs/ 下）
        test_name = report.nodeid.replace("::", "_").replace("/", "_").replace("\\", "_")
        screenshot_glob = os.path.join("logs", f"{test_name}*.png")
        import glob as _glob
        shots = _glob.glob(screenshot_glob)
        shot_path = shots[-1] if shots else ""

        # 提取失败/错误信息
        failure_msg = ""
        if report.failed:
            failure_msg = str(report.longreprtext) if hasattr(report, "longreprtext") else ""
            # 清理 traceback，只留关键行
            if "AssertionError" in failure_msg:
                lines = failure_msg.splitlines()
                for ln in lines:
                    if "AssertionError" in ln:
                        failure_msg = ln.strip()
                        break

        _test_results.append({
            "nodeid":    report.nodeid,
            "outcome":   report.outcome,       # passed / failed / skipped
            "duration":  round(report.duration, 3),
            "title":     report.nodeid.split("::")[-1].replace("_", " "),
            "module":    report.nodeid.split("::")[0].split("/")[-1].replace("test_", "").replace(".py", ""),
            "screenshot": shot_path,
            "failure_msg": failure_msg[:500],
            "stdout":   "",
        })
        
        # 实时保存到临时文件（避免 worker 崩溃丢失数据）
        _save_worker_results()


def pytest_sessionfinish(session, exitstatus):
    """所有测试结束后，合并所有 worker 结果并写 JSON"""
    global _session_start
    
    # 再次保存当前 worker 结果
    _save_worker_results()
    
    # 只有 master 进程（或没有 xdist 时）合并所有结果
    worker_id = _get_worker_id()
    if worker_id == "master":
        # 等待所有 worker 完成（简单等待）
        _time.sleep(1)
        
        # 合并所有 worker 结果
        all_results = _merge_all_worker_results()
        
        report_dir = os.path.join(os.path.dirname(__file__), "reports")
        os.makedirs(report_dir, exist_ok=True)

        # 汇总
        passed  = sum(1 for r in all_results if r["outcome"] == "passed")
        failed  = sum(1 for r in all_results if r["outcome"] == "failed")
        skipped = sum(1 for r in all_results if r["outcome"] == "skipped")
        total   = len(all_results)
        duration = round(_time.time() - _session_start, 1) if _session_start else 0

        data = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platform":     "Windows (Playwright)",
            "total":        total,
            "passed":       passed,
            "failed":       failed,
            "skipped":      skipped,
            "pass_rate":    f"{round(passed/total*100, 1) if total else 0}%",
            "duration_s":   duration,
            "exitstatus":   exitstatus,
            "tests":        all_results,
        }

        out_path = os.path.join(report_dir, "report_data.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n[Report] JSON written: {out_path} ({total} tests)")


def _should_run_headless():
    """判断是否需要 headless 模式：无桌面环境（cron/CI/远程）自动切换"""
    # 环境变量显式指定
    env = os.environ.get("PLAYWRIGHT_HEADLESS", "").lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    # Windows: 无交互式桌面站 → headless
    if os.name == "nt":
        session_name = os.environ.get("SESSIONNAME", "")
        # 没有 SESSIONNAME 或包含 RDP/Service 字样 → 无桌面
        if not session_name or "RDP" in session_name.upper() or "Service" in session_name:
            # 再检查是否有 Explorer 进程（桌面存在的标志）
            try:
                import subprocess
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq explorer.exe"],
                    capture_output=True, text=True, timeout=5
                )
                if "explorer.exe" not in result.stdout:
                    return True
            except Exception:
                return True
    # Linux/macOS: 无 DISPLAY → headless
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        return True
    return False


@pytest.fixture(scope="function")
def browser():
    """
    函数级浏览器（每个测试用例独占一个 Chromium 实例，完全隔离。

    根因：session-scoped browser + pytest-xdist 多 worker 并发创建 context =
    Chromium IPC 竞争，导致 worker 进程崩溃 ("Not properly terminated")。
    改为 function-scope 后，每个 worker 的每个测试使用独立浏览器，不存在共享。

    关键：每个测试后必须完整关闭 Playwright 实例（pw.stop()），否则 Windows
    ProactorEventLoop 背景线程的 is_running() 会保持 True，导致后续测试报错
    "asyncio loop inside"。在子线程执行 stop() 可避免 C 扩展 teardown hang。
    """
    headless = _should_run_headless()
    print(f"[conftest] Browser headless={headless}")
    pw = sync_playwright().start()
    chromium = pw.chromium.launch(headless=headless)
    yield chromium
    # 函数级 teardown：正常关闭 Playwright
    try:
        chromium.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass


# ── 登录测试用（function scope，隔离 cookie）─────────────────────

@pytest.fixture(scope="function")
def context(browser):
    """函数级 Context（每个测试用例独立上下文，cookie 不互相污染）"""
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    yield ctx
    try:
        ctx.close()
    except Exception:
        pass


@pytest.fixture(scope="function")
def page(context):
    """函数级 Page（每个测试用例独占一页）"""
    p = context.new_page()
    yield p
    try:
        p.close()
    except Exception:
        pass


@pytest.fixture(scope="function")
def login_page(page):
    """登录页面对象 fixture（function scope，每次清 cookie 重新登录）"""
    from pages.login_page import LoginPage
    lp = LoginPage(page)
    lp.goto()
    return lp


# ── 共享登录辅助 ──────────────────────────────────────────────

VALID_PHONE = "13757188737"
VALID_CODE = "8888"


def _do_login(lp):
    """完成完整登录流程（填写 + 提交 + 处理弹窗）"""
    lp.fill_phone(VALID_PHONE)
    lp.fill_code(VALID_CODE)
    lp.submit()
    lp.handle_after_submit()
    return lp


# ── 工作台测试用（module scope，共享已登录 context）─────────────────────

@pytest.fixture(scope="function")
def logged_in_context(browser):
    """
    函数级已登录 Context（依赖 function-scoped browser，每个测试完全隔离）。

    架构：browser(function) -> context(function) -> page(function)
    每个测试用例拥有独立的 Chromium 实例，完全不存在跨测试共享。
    login cookie 存在 context 中，page.close() 后 context 保持 cookie。
    """
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()

    # 执行登录
    from pages.login_page import LoginPage
    lp = LoginPage(page)
    lp.goto()
    _do_login(lp)

    # 登录成功后，cookie 已保存在 context 中
    # 后续每个用例只需新建 page，无需重新登录
    page.close()

    yield ctx
    # 不调用 ctx.close() — Playwright teardown hang 会阻塞后续所有测试，
    # pytest-timeout 无法中断 C 扩展线程的 close() 调用。
    # OS 在 pytest 进程退出时自动回收资源。


@pytest.fixture(scope="function")
def workbench_page(logged_in_context):
    """
    工作台页面对象 fixture。
    复用模块级已登录 context，每个用例只新建 page（不重新登录）。
    自动导航到工作台。
    """
    from pages.workbench_page import WorkbenchPage

    # 工作台 URL（支持多环境）
    import os as _os
    _env = _os.environ.get("TEST_ENV", "test")
    if _env == "pre":
        _wb_base = "https://pre-cloud.jingfire.com"
        _nav_timeout = 60000  # 预发布环境需要更长的等待时间
    else:
        _wb_base = "https://test6688.jh119.cn"
        _nav_timeout = 30000
    page = logged_in_context.new_page()
    page.goto(f"{_wb_base}/business/#/workbench", wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.wait_for_selector("a[href^='#/']", timeout=_nav_timeout)

    wp = WorkbenchPage(page)
    yield wp
    # 不调用 page.close()，同上


# ── 合同管理测试用（module scope）─────────────────────────────

@pytest.fixture(scope="function")
def contract_page(logged_in_context):
    """
    合同管理页面 fixture。
    复用模块级已登录 context，每个用例只新建 page（不重新登录）。
    自动导航到合同管理页面。
    """
    from pages.contract_page import ContractPage

    page = logged_in_context.new_page()
    cp = ContractPage(page)
    cp.goto()
    yield cp
    # 不调用 page.close()，同上
