"""
WorkbenchPage — 工作台页面对象
封装工作台页面的所有 UI 交互，包括导航菜单、头部区域、快捷操作。
"""
import time
from playwright.sync_api import Page


class WorkbenchPage:
    """工作台页面对象"""

    def __init__(self, page: Page):
        self.page = page

    # ── URL / 状态判断 ──────────────────────────────────────────

    @property
    def url(self) -> str:
        return self.page.url

    def is_at_workbench(self) -> bool:
        """判断是否在工作台"""
        return "#/workbench" in self.page.url

    # ── 导航菜单 ──────────────────────────────────────────────

    # 侧边栏导航项 (href -> 中文名映射)
    NAV_ITEMS = {
        "workbench":        {"href": "#/workbench",        "name": "工作台"},
        "project":          {"href": "#/project",          "name": "项目管理"},
        "unitInfo":         {"href": "#/unitInfo",         "name": "单位管理"},
        "contract":         {"href": "#/contract",         "name": "合同管理"},
        "task":             {"href": "#/task",             "name": "任务管理"},
        "statistics":       {"href": "#/statistics",       "name": "数据统计"},
        "payContract":      {"href": "#/payContract",      "name": "支付合同"},
        "receivePayment":   {"href": "#/receivePayment",   "name": "收款管理"},
        "fundAccount":      {"href": "#/fundAccount",      "name": "资金账户"},
        "materials":        {"href": "#/materials",        "name": "材料目录"},
        "invoiceManagement":{"href": "#/invoiceManagement","name": "发票管理"},
        "purchaseApply":    {"href": "#/purchaseApply",    "name": "采购申请"},
        "maintenance":      {"href": "#/maintenance",      "name": "设施维护"},
        "purchaseOrder":    {"href": "#/purchaseOrder",    "name": "采购订单"},
        "storage":          {"href": "#/storage",          "name": "仓储采购"},
    }

    def get_nav_links_count(self) -> int:
        """获取侧边栏导航链接数量"""
        return self.page.locator("a[href^='#/']").count()

    def get_visible_nav_items(self) -> list[str]:
        """获取所有可见导航项的 href"""
        items = []
        links = self.page.locator("a[href^='#/']")
        for i in range(links.count()):
            try:
                href = links.nth(i).get_attribute("href") or ""
                if href.startswith("#/"):
                    items.append(href)
            except Exception:
                pass
        return items

    def click_nav_item(self, key: str):
        """
        点击侧边栏导航项
        key: NAV_ITEMS 中的键名，如 "project", "contract" 等
        """
        info = self.NAV_ITEMS.get(key)
        if not info:
            raise ValueError(f"未知导航项: {key}，可选: {list(self.NAV_ITEMS.keys())}")
        link = self.page.locator(f"a[href='{info['href']}']")
        if link.count() == 0:
            raise AssertionError(f"导航项 [{info['name']}] 未找到: {info['href']}")
        link.first.click()
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(1000)

    def is_nav_item_visible(self, key: str) -> bool:
        """检查导航项是否可见"""
        info = self.NAV_ITEMS.get(key)
        if not info:
            return False
        link = self.page.locator(f"a[href='{info['href']}']")
        return link.count() > 0 and link.first.is_visible()

    # ── 头部区域 ──────────────────────────────────────────────

    def get_header_text(self) -> str:
        """获取顶部 Header 区域文字"""
        header = self.page.locator("header").first
        if header.count() > 0:
            try:
                return header.inner_text()
            except Exception:
                pass
        return ""

    def has_search_input(self) -> bool:
        """检查顶部搜索框是否存在"""
        # header 中有搜索图标
        search_icon = self.page.locator(".anticon-search, [class*='headerSearch']")
        return search_icon.count() > 0

    # ── 快捷按钮 ──────────────────────────────────────────────

    def get_visible_buttons_text(self) -> list[str]:
        """获取所有可见按钮的文字"""
        texts = []
        btns = self.page.locator("button:visible")
        for i in range(btns.count()):
            try:
                texts.append(btns.nth(i).inner_text().strip())
            except Exception:
                pass
        return texts

    # ── 截图 ──────────────────────────────────────────────

    def screenshot(self, path: str):
        self.page.screenshot(path=path)
