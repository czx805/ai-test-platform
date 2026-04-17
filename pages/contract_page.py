"""
ContractPage — 合同管理页面对象
URL: https://test6688.jh119.cn/business/#/contract
"""
import time
from playwright.sync_api import Page, Locator


class ContractPage:
    """合同管理页面对象"""

    URL = "https://test6688.jh119.cn/business/#/contract"

    # 顶部统计卡片顺序（无 title label，按索引映射）
    # [0]合同总数 [1]全部合同 [2]合同标的总额 [3]合同总金额
    # [4]已生效合同数 [5]待签署合同数 [6]已开票未回款合同数
    # [7]失效合同数(占比) [8]失效合同占比
    STAT_MAPPING = {
        0: "合同总数",
        1: "全部合同",
        2: "合同标的总额",
        3: "合同总金额",
        4: "已生效合同数",
        5: "待签署合同数",
        6: "已开票未回款合同数",
        7: "失效合同数",
        8: "失效合同占比",
    }

    def __init__(self, page: Page):
        self.page = page

    # ── 导航 & 状态 ──────────────────────────────────────────

    @property
    def url(self) -> str:
        return self.page.url

    def is_at_contract(self) -> bool:
        return "#/contract" in self.page.url

    def goto(self):
        self.page.goto(self.URL)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)

    def screenshot(self, path: str):
        self.page.screenshot(path=path)

    # ── 统计卡片 ─────────────────────────────────────────────

    def get_stat_value(self, keyword: str = None, index: int = None) -> str:
        """
        获取统计值。
        - keyword: 通过关键词匹配（如 "合同总数"）
        - index: 直接通过索引获取（0=合同总数, 5=待签署, 7=失效合同数）
        """
        stats = self.page.locator('.ant-statistic').all()
        if index is not None:
            if index < len(stats):
                return stats[index].inner_text().strip()
            return ""
        if keyword:
            # 先尝试按索引映射
            for idx, name in self.STAT_MAPPING.items():
                if keyword in name and idx < len(stats):
                    return stats[idx].inner_text().strip()
            # 兜底：遍历所有 stat
            for stat in stats:
                try:
                    if keyword in stat.inner_text():
                        return stat.inner_text().strip()
                except Exception:
                    pass
        return ""

    # ── 搜索区域 ─────────────────────────────────────────────

    def expand_filters(self):
        """展开高级筛选区域"""
        expand_btn = self.page.locator('.ant-pro-query-filter-collapse-button, a:has-text("展开")')
        if expand_btn.count() > 0:
            expand_btn.first.click(force=True)
            self.page.wait_for_timeout(1000)

    def fill_search(self, keyword: str, value: str):
        """填写搜索框（keyword 只用于报错提示）"""
        self.expand_filters()
        self.page.wait_for_timeout(500)
        # 优先用 ID 定位（#contractNumber 最可靠）
        inp = self.page.locator('#contractNumber')
        if inp.count() == 0:
            raise AssertionError("未找到 #contractNumber 输入框")
        inp.first.fill(value, force=True)
        self.page.wait_for_timeout(300)

    def click_reset(self):
        """点击重置按钮（button[4]）"""
        btns = self.page.locator('button')
        # button[2]="重 置"
        btn = btns.nth(2)
        btn.click(force=True)
        self.page.wait_for_timeout(1000)

    def click_query(self):
        """点击查询按钮（button[3]）"""
        btns = self.page.locator('button')
        # button[3]="查 询"
        btn = btns.nth(3)
        btn.click(force=True)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)

    # ── 表格 ─────────────────────────────────────────────────

    def get_table_row_count(self) -> int:
        rows = self.page.locator('.ant-table-tbody tr.ant-table-row')
        return rows.count()

    def get_total_rows_hint(self) -> str:
        el = self.page.locator('.ant-pagination-total-text, .ant-pagination')
        if el.count() > 0:
            return el.first.inner_text().strip()
        return ""

    def click_pagination(self, page_num: int):
        link = self.page.locator(f'.ant-pagination-item a:text-is("{page_num}")')
        if link.count() > 0:
            link.first.click(force=True)
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(1500)
        else:
            raise AssertionError(f"未找到页码 {page_num}")

    def get_all_rows_data(self) -> list[dict]:
        headers = self.page.locator('.ant-table-thead th')
        header_list = []
        for i in range(headers.count()):
            try:
                header_list.append(headers.nth(i).inner_text().strip())
            except Exception:
                header_list.append("")
        if not header_list:
            return []

        rows = self.page.locator('.ant-table-tbody tr.ant-table-row')
        result = []
        for i in range(rows.count()):
            try:
                cells = rows.nth(i).locator('td').all()
                if len(cells) >= len(header_list):
                    row_dict = {}
                    for j, h in enumerate(header_list):
                        if h:
                            try:
                                row_dict[h] = cells[j].inner_text().strip()
                            except Exception:
                                row_dict[h] = ""
                    if row_dict:
                        result.append(row_dict)
            except Exception:
                pass
        return result

    # ── 新建合同 ─────────────────────────────────────────────

    def click_new_contract(self):
        """点击新建合同按钮（button[5]）"""
        btns = self.page.locator('button')
        btn = btns.nth(5)
        btn_text = btn.inner_text().strip()
        if '新建' not in btn_text and '合同' not in btn_text:
            raise AssertionError(f"button[5] 不是新建合同按钮（当前文本: {btn_text}）")
        btn.click(force=True)
        self.page.wait_for_timeout(2000)

    def is_modal_visible(self) -> bool:
        modal = self.page.locator('.ant-modal')
        if modal.count() == 0:
            return False
        try:
            return modal.first.is_visible()
        except Exception:
            return False

    def modal_get_labels(self) -> list[str]:
        labels = self.page.locator('.ant-modal .ant-form-item-label label')
        result = []
        for i in range(labels.count()):
            try:
                result.append(labels.nth(i).inner_text().strip())
            except Exception:
                result.append("")
        return result

    def modal_fill_by_index(self, field_index: int, value: str):
        modal_inputs = self.page.locator('.ant-modal input')
        count = modal_inputs.count()
        if field_index >= count:
            raise AssertionError(f"字段索引 {field_index} 超出范围（共 {count} 个 input）")
        modal_inputs.nth(field_index).fill(value)
        self.page.wait_for_timeout(300)

    def click_modal_button(self, text_keyword: str):
        btns = self.page.locator('.ant-modal button')
        for i in range(btns.count()):
            txt = btns.nth(i).inner_text().strip()
            if text_keyword in txt:
                btns.nth(i).click(force=True)
                self.page.wait_for_timeout(1000)
                return
        raise AssertionError(f"未找到弹窗中包含 '{text_keyword}' 的按钮")

    def close_modal(self):
        try:
            close_btn = self.page.locator('.ant-modal .ant-modal-close, .ant-modal-close')
            if close_btn.count() > 0:
                close_btn.first.click(force=True)
                self.page.wait_for_timeout(1000)
                return
        except Exception:
            pass
        self.click_modal_button("取消")

    # ── 合同详情 ─────────────────────────────────────────────

    def click_detail_link(self, row_index: int = 0):
        """点击"查看详情"（是 span.primary.pointer，不是 a 标签）"""
        detail_spans = self.page.locator('.ant-table-cell .primary.pointer, td:last-child .primary.pointer')
        # 尝试更通用的选择器
        if detail_spans.count() == 0:
            # 找表格单元格中的所有可点击元素
            rows = self.page.locator('.ant-table-tbody tr.ant-table-row')
            if row_index >= rows.count():
                raise AssertionError(f"行索引 {row_index} 超出范围（共 {rows.count()} 行）")
            last_cell = rows.nth(row_index).locator('td').last
            detail_spans = last_cell.locator('.primary.pointer, span[class*="pointer"]')
        count = detail_spans.count()
        if row_index >= count:
            raise AssertionError(f"行索引 {row_index} 超出范围（共 {count} 个查看详情）")
        detail_spans.nth(row_index).click(force=True)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)

    def is_detail_page(self) -> bool:
        url = self.page.url
        return ("detail" in url.lower() or "/detail" in url or "?id=" in url)
