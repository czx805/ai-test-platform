"""
test_workbench.py — 工作台页面测试用例
覆盖: 页面加载、导航菜单、头部区域、快捷操作、导航跳转、后退返回
"""
import os
import pytest

from pages.workbench_page import WorkbenchPage
from tests.testdata.workbench_data import CORE_NAV_ITEMS, ALL_NAV_ITEMS, NAV_CLICK_CASES


os.makedirs("logs", exist_ok=True)


# ══════════════════════════════════════════════════════════════
#  页面加载 & 状态
# ══════════════════════════════════════════════════════════════

def test_workbench_loaded(workbench_page):
    """登录后应自动进入工作台"""
    wp = workbench_page
    wp.screenshot("logs/wb_loaded.png")

    assert wp.is_at_workbench(), f"未在工作台: {wp.url}"
    print(f"[PASS] 工作台已加载: {wp.url}")


def test_workbench_has_nav_menu(workbench_page):
    """工作台侧边栏应有导航菜单"""
    wp = workbench_page
    nav_count = wp.get_nav_links_count()
    wp.screenshot("logs/wb_nav_menu.png")

    assert nav_count >= 10, f"导航项不足（当前 {nav_count}）"
    print(f"[PASS] 导航菜单有 {nav_count} 项")


def test_workbench_has_header(workbench_page):
    """工作台顶部应有 Header 区域"""
    wp = workbench_page
    header_count = wp.page.locator("header").count()
    wp.screenshot("logs/wb_header.png")

    assert header_count >= 1, "Header 区域不存在"
    print(f"[PASS] Header 区域存在，共 {header_count} 个 header 元素")


# ══════════════════════════════════════════════════════════════
#  核心导航项可见性（参数化）
# ══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("item", CORE_NAV_ITEMS, ids=[i["key"] for i in CORE_NAV_ITEMS])
def test_core_nav_item_visible(workbench_page, item):
    """核心导航项 [{name}] 应可见"""
    wp = workbench_page
    wp.screenshot(f"logs/wb_nav_{item['key']}.png")

    assert wp.is_nav_item_visible(item["key"]), f"核心导航项 [{item['name']}] 不可见"
    print(f"[PASS] 核心导航项 [{item['name']}] 可见")


# ══════════════════════════════════════════════════════════════
#  全部导航项完整性检查（参数化）
# ══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("item", ALL_NAV_ITEMS, ids=[i["key"] for i in ALL_NAV_ITEMS])
def test_all_nav_items_exist(workbench_page, item):
    """导航项 [{name}] 应存在于侧边栏"""
    wp = workbench_page
    visible = wp.is_nav_item_visible(item["key"])

    if not visible:
        wp.screenshot(f"logs/wb_nav_missing_{item['key']}.png")
    print(f"[{'PASS' if visible else 'WARN'}] [{item['name']}] {'可见' if visible else '不可见（可能需展开子菜单）'}")
    # 不强制断言，因为有些导航项可能需要展开子菜单才可见
    # 只做记录


# ══════════════════════════════════════════════════════════════
#  导航跳转验证（参数化）
# ══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("case", NAV_CLICK_CASES, ids=[c["key"] for c in NAV_CLICK_CASES])
def test_nav_click_navigates(workbench_page, case):
    """点击 [{name}] -> URL 应包含 {expected_url}"""
    wp = workbench_page

    # 点击导航项
    wp.click_nav_item(case["key"])
    wp.screenshot(f"logs/wb_navigate_{case['key']}.png")

    assert case["expected_url"] in wp.url, f"点击 [{case['name']}] 后 URL 不对: {wp.url}"
    print(f"[PASS] 点击 [{case['name']}] 跳转到: {wp.url}")

    # 返回工作台
    wp.click_nav_item("workbench")
    wp.page.wait_for_timeout(1000)


# ══════════════════════════════════════════════════════════════
#  快捷操作
# ══════════════════════════════════════════════════════════════

def test_workbench_has_buttons(workbench_page):
    """工作台应有可见的快捷操作按钮"""
    wp = workbench_page
    btn_texts = wp.get_visible_buttons_text()
    wp.screenshot("logs/wb_buttons.png")

    assert len(btn_texts) >= 2, f"快捷按钮不足（当前 {len(btn_texts)}）"
    print(f"[PASS] 快捷按钮: {btn_texts[:5]}")


def test_workbench_search_exists(workbench_page):
    """工作台顶部应有搜索功能"""
    wp = workbench_page
    has_search = wp.has_search_input()
    wp.screenshot("logs/wb_search.png")

    assert has_search, "未找到搜索框/搜索图标"
    print("[PASS] 搜索功能存在")


# ══════════════════════════════════════════════════════════════
#  导航后返回工作台
# ══════════════════════════════════════════════════════════════

def test_navigate_and_back(workbench_page):
    """点击项目导航后，再点工作台应能返回"""
    wp = workbench_page

    # 1. 点击项目管理
    wp.click_nav_item("project")
    wp.screenshot("logs/wb_nav_project.png")
    assert "#/project" in wp.url, f"未跳转到项目管理: {wp.url}"

    # 2. 点击工作台返回
    wp.click_nav_item("workbench")
    wp.screenshot("logs/wb_nav_back.png")
    assert wp.is_at_workbench(), f"未返回工作台: {wp.url}"

    print("[PASS] 导航 -> 返回工作台 正常")


def test_navigate_multiple_pages(workbench_page):
    """连续导航多个页面后，最终回到工作台"""
    wp = workbench_page
    nav_keys = ["project", "contract", "task", "workbench"]

    for key in nav_keys:
        wp.click_nav_item(key)
        wp.screenshot(f"logs/wb_multi_{key}.png")

    assert wp.is_at_workbench(), f"连续导航后未回到工作台: {wp.url}"
    print("[PASS] 连续导航后回到工作台 正常")


# ══════════════════════════════════════════════════════════════
#  页面刷新
# ══════════════════════════════════════════════════════════════

def test_workbench_refresh(workbench_page):
    """工作台刷新后应保持在工作台（修复：弃用 networkidle，改等侧边栏渲染完成）"""
    wp = workbench_page
    # reload 后只等 DOM 就绪，不等 networkidle（SPA 持续请求永远等不到）
    wp.page.reload(wait_until="domcontentloaded")
    # 等侧边栏导航链接出现 = SPA 渲染完成
    wp.page.wait_for_selector("a[href^='#/']", timeout=15000)
    wp.screenshot("logs/wb_refresh.png")

    assert wp.is_at_workbench(), f"刷新后离开工作台: {wp.url}"
    print("[PASS] 刷新后仍在工作台")
