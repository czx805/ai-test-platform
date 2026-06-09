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


# ── Cookie 缓存优化：避免每个测试重新登录 ─────────────────────

import hashlib
import threading

# Cookie 缓存文件路径
_COOKIE_CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cookie_cache")
_COOKIE_CACHE_LOCK = threading.Lock()

def _get_cookie_cache_key():
    """生成 cookie 缓存文件 key（基于环境）"""
    env = os.environ.get("TEST_ENV", "test")
    phone = "13757188737"  # VALID_PHONE
    return hashlib.md5(f"{env}_{phone}".encode()).hexdigest()

def _get_cookie_cache_file():
    """获取 cookie 缓存文件路径"""
    os.makedirs(_COOKIE_CACHE_DIR, exist_ok=True)
    key = _get_cookie_cache_key()
    return os.path.join(_COOKIE_CACHE_DIR, f"{key}.json")

def _save_cookies_to_cache(cookies):
    """保存 cookies 到缓存文件"""
    cache_file = _get_cookie_cache_file()
    with _COOKIE_CACHE_LOCK:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({
                "cookies": cookies,
                "timestamp": time.time(),
                "env": os.environ.get("TEST_ENV", "test")
            }, f)
    print(f"[cookie_cache] Saved to {cache_file}")

def _load_cookies_from_cache():
    """从缓存文件加载 cookies，如果不存在或过期返回 None"""
    cache_file = _get_cookie_cache_file()
    if not os.path.exists(cache_file):
        return None
    
    try:
        with _COOKIE_CACHE_LOCK:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # 检查环境是否匹配
        if data.get("env") != os.environ.get("TEST_ENV", "test"):
            return None
        
        # 检查是否过期（30分钟）
        if time.time() - data.get("timestamp", 0) > 1800:
            print(f"[cookie_cache] Cache expired (>30min)")
            return None
        
        print(f"[cookie_cache] Loaded from cache")
        return data.get("cookies")
    except Exception as e:
        print(f"[cookie_cache] Load failed: {e}")
        return None

def _clear_cookie_cache():
    """清除 cookie 缓存"""
    cache_file = _get_cookie_cache_file()
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print(f"[cookie_cache] Cleared")


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
    函数级已登录 Context（每个测试一个 context，但复用 cookies）。
    
    优化策略：
    1. 第一个测试：完整登录（约 30s），保存 cookies
    2. 后续测试：加载 cookies（约 1s），跳过登录
    
    注意：每个测试仍然有独立的 context（保证隔离性），
    但通过 cookie 缓存避免重复登录流程。
    """
    from pages.login_page import LoginPage
    import os as _os
    
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    
    # 尝试加载缓存的 cookies
    cached_cookies = _load_cookies_from_cache()
    
    if cached_cookies:
        ctx.add_cookies(cached_cookies)
        print("[logged_in_context] Loaded cached cookies")
    else:
        # 缓存不存在或过期，执行完整登录
        print("[logged_in_context] No valid cache, performing full login...")
        page = ctx.new_page()
        lp = LoginPage(page)
        lp.goto()
        _do_login(lp)
        page.close()
        
        # 保存 cookies
        cookies = ctx.cookies()
        _save_cookies_to_cache(cookies)
        print("[logged_in_context] Logged in and saved cookies")
    
    yield ctx
    # 不调用 ctx.close()，避免 teardown hang


@pytest.fixture(scope="function")
def workbench_page(logged_in_context):
    """
    工作台页面对象 fixture。
    复用已登录 context，每个用例只新建 page。
    
    优化：
    1. 增加导航超时（60秒）
    2. 简化等待逻辑，只用 domcontentloaded
    3. 导航菜单等待时间缩短到 10秒
    """
    from pages.workbench_page import WorkbenchPage
    import os as _os
    
    _env = _os.environ.get("TEST_ENV", "test")
    _wb_base = "https://pre-cloud.jingfire.com" if _env == "pre" else "https://test6688.jh119.cn"
    
    page = logged_in_context.new_page()
    
    # 导航到工作台（增加超时）
    page.goto(f"{_wb_base}/business/#/workbench", wait_until="domcontentloaded", timeout=60000)
    
    # 等待导航菜单（缩短时间）
    try:
        page.wait_for_selector("a[href^='#/']", timeout=10000)
    except Exception:
        # 如果超时，继续执行，让测试自己去判断
        pass
    
    wp = WorkbenchPage(page)
    yield wp
    # 不调用 page.close()，避免 teardown hang


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
