"""
conftest.py — pytest fixtures
提供浏览器、页面等共享资源，支持所有测试用例。

策略：
- 登录测试（test_login）：function scope，每个用例独立 context + page，保证隔离
- 工作台测试（test_workbench）：module scope 共享已登录 context，避免重复登录
"""
import json
import os
import time
from datetime import datetime
import pytest
from playwright.sync_api import sync_playwright

# ── 自定义报告钩子：收集结果写 JSON ──────────────────────────────
import time as _time

_test_results = []        # list[dict]
_session_start = None     # session 开始时间


def pytest_configure(config):
    pass  # no-op


def pytest_sessionstart(session):
    global _session_start
    _session_start = _time.time()


def pytest_runtest_logreport(report):
    """收集每个测试用例的运行时信息"""
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


def pytest_sessionfinish(session, exitstatus):
    """所有测试结束后，写 JSON 供报告生成脚本使用"""
    global _session_start
    report_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(report_dir, exist_ok=True)

    # 汇总
    passed  = sum(1 for r in _test_results if r["outcome"] == "passed")
    failed  = sum(1 for r in _test_results if r["outcome"] == "failed")
    skipped = sum(1 for r in _test_results if r["outcome"] == "skipped")
    total   = len(_test_results)
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
        "tests":        _test_results,
    }

    out_path = os.path.join(report_dir, "report_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[Report] JSON written: {out_path}")


@pytest.fixture(scope="session")
def browser():
    """会话级浏览器（所有测试共享一个实例，最高效）"""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False)
    yield browser
    # 强制关闭所有 context 和 page
    try:
        for ctx in browser.contexts:
            for pg in ctx.pages:
                try:
                    pg.close()
                except Exception:
                    pass
            ctx.close()
    except Exception:
        pass
    browser.close()
    pw.stop()


# ── 登录测试用（function scope，隔离 cookie） ──────────────────────

@pytest.fixture(scope="function")
def context(browser):
    """函数级 Context（每个测试用例独立上下文，cookie 不互相污染）"""
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(context):
    """函数级 Page（每个测试用例独占一页）"""
    p = context.new_page()
    yield p
    p.close()


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


# ── 工作台测试用（module scope，共享已登录 context） ──────────────────────

@pytest.fixture(scope="module")
def logged_in_context(browser):
    """
    模块级已登录 Context。
    登录一次，保存 cookie，整个 test_workbench.py 共享。
    大幅减少重复登录耗时。
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
    ctx.close()


@pytest.fixture(scope="function")
def workbench_page(logged_in_context):
    """
    工作台页面对象 fixture。
    复用模块级已登录 context，每个用例只新建 page（不重新登录）。
    自动导航到工作台。
    """
    from pages.workbench_page import WorkbenchPage

    page = logged_in_context.new_page()
    page.goto("https://test6688.jh119.cn/business/#/workbench")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    wp = WorkbenchPage(page)
    yield wp
    page.close()


# ── 合同管理测试用（module scope） ──────────────────────────────

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
    page.close()
