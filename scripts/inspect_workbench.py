"""
inspect_workbench.py — 工作台页面结构探查脚本
登录后截图并打印关键元素，用于编写 WorkbenchPage 和测试用例
"""
from playwright.sync_api import sync_playwright
import os

os.makedirs("logs", exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()

    # ── 登录 ──────────────────────────────────────────────
    page.goto("https://test6688.jh119.cn/business/#/login")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    page.locator("input").nth(0).fill("13757188737")
    page.locator("input").nth(1).fill("8888")
    page.locator("input").nth(1).press("Enter")
    page.wait_for_timeout(4000)

    # ── 处理弹窗 + 进入单位 ──────────────────────────────────────
    # 等待 URL 变化（最多 15s）
    for _ in range(15):
        page.wait_for_timeout(1000)
        if "#/login" not in page.url:
            break

    # 多轮处理 Modal 和"进入该单位"按钮
    for round_i in range(5):
        # 尝试点"进入该单位"
        unit_btn = page.locator("button:has-text('进入该单位')")
        if unit_btn.count() > 0:
            try:
                unit_btn.first.click(force=True)
                page.wait_for_timeout(2000)
            except Exception:
                pass

        # 关闭 Modal
        modal = page.locator(".ant-modal-wrap")
        if modal.count() > 0:
            try:
                close_btn = page.locator(".ant-modal-close, .ant-modal-close-x").first
                if close_btn.count() > 0:
                    close_btn.click(force=True)
                else:
                    page.locator(".ant-modal button").first.click(force=True)
                page.wait_for_timeout(1500)
            except Exception:
                pass

        # 检查是否已到工作台
        if "#/login" not in page.url:
            break

    # 再等一下让页面完全加载
    page.wait_for_timeout(3000)
    print("URL:", page.url)
    page.screenshot(path="logs/workbench_inspect.png")

    # ── 页面标题 ──────────────────────────────────────────────
    print("Title:", page.title())

    # ── 导航菜单 ──────────────────────────────────────────────
    navs = page.locator(".ant-menu-item, .ant-menu-submenu-title")
    print(f"\n[Nav] {navs.count()} items:")
    for i in range(min(navs.count(), 30)):
        try:
            print(f"  nav[{i}]: {navs.nth(i).inner_text().strip()}")
        except Exception:
            pass

    # ── 顶部 Header ──────────────────────────────────────────────
    header = page.locator("header, .ant-layout-header, [class*='header']")
    print(f"\n[Header] {header.count()} elements")
    for i in range(min(header.count(), 5)):
        try:
            txt = header.nth(i).inner_text().strip()[:80]
            cls = header.nth(i).get_attribute("class") or ""
            print(f"  header[{i}] class={cls[:50]}: {txt}")
        except Exception:
            pass

    # ── 卡片/面板 ──────────────────────────────────────────────
    cards = page.locator(".ant-card")
    print(f"\n[Cards] {cards.count()} cards:")
    for i in range(min(cards.count(), 10)):
        try:
            title_el = cards.nth(i).locator(".ant-card-head-title")
            title = title_el.inner_text().strip() if title_el.count() > 0 else "(no title)"
            print(f"  card[{i}]: {title}")
        except Exception:
            pass

    # ── 统计数字 ──────────────────────────────────────────────
    stats = page.locator(".ant-statistic, [class*='statistic'], [class*='count-num']")
    print(f"\n[Stats] {stats.count()} elements:")
    for i in range(min(stats.count(), 10)):
        try:
            print(f"  stat[{i}]: {stats.nth(i).inner_text().strip()[:60]}")
        except Exception:
            pass

    # ── 按钮 ──────────────────────────────────────────────
    btns = page.locator("button:visible")
    print(f"\n[Buttons] {btns.count()} visible buttons:")
    for i in range(min(btns.count(), 15)):
        try:
            print(f"  btn[{i}]: {btns.nth(i).inner_text().strip()}")
        except Exception:
            pass

    # ── 链接 ──────────────────────────────────────────────
    links = page.locator("a:visible")
    print(f"\n[Links] {links.count()} visible links:")
    for i in range(min(links.count(), 15)):
        try:
            href = links.nth(i).get_attribute("href") or ""
            txt = links.nth(i).inner_text().strip()
            print(f"  a[{i}]: {txt} -> {href}")
        except Exception:
            pass

    # ── 表格 ──────────────────────────────────────────────
    tables = page.locator(".ant-table, table")
    print(f"\n[Tables] {tables.count()} tables")

    # ── 面包屑 ──────────────────────────────────────────────
    breadcrumb = page.locator(".ant-breadcrumb")
    print(f"\n[Breadcrumb] {breadcrumb.count()} elements:")
    for i in range(breadcrumb.count()):
        try:
            print(f"  breadcrumb[{i}]: {breadcrumb.nth(i).inner_text().strip()}")
        except Exception:
            pass

    browser.close()
    print("\n[DONE] 截图已保存到 logs/workbench_inspect.png")
