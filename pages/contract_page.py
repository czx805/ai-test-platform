"""
ContractPage — 合同管理页面对象（支持 CRUD 操作）
URL: https://test6688.jh119.cn/business/#/contract/list
"""
import time
from playwright.sync_api import Page, Locator


def _safe_networkidle(page, timeout=15000):
    """等待 networkidle，超时后降级为 domcontentloaded（防止无头模式卡死）"""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass


class ContractPage:
    """合同管理页面对象"""

    URL = "https://test6688.jh119.cn/business/#/contract/list"

    # 顶部统计卡片顺序（按索引映射）
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
        self.page.goto(self.URL, wait_until="domcontentloaded")
        _safe_networkidle(self.page)
        self.page.wait_for_selector(".ant-table", timeout=15000)
        self.page.wait_for_timeout(2000)

    def screenshot(self, path: str):
        self.page.screenshot(path=path)

    # ── 统计卡片 ─────────────────────────────────────────────

    def get_stat_value(self, keyword: str = None, index: int = None) -> str:
        stats = self.page.locator(".ant-statistic").all()
        if index is not None:
            if index < len(stats):
                return stats[index].inner_text().strip()
            return ""
        if keyword:
            for idx, name in self.STAT_MAPPING.items():
                if keyword in name and idx < len(stats):
                    return stats[idx].inner_text().strip()
            for stat in stats:
                try:
                    if keyword in stat.inner_text():
                        return stat.inner_text().strip()
                except Exception:
                    pass
        return ""

    # ── 搜索区域 ─────────────────────────────────────────────

    def expand_filters(self):
        expand_btn = self.page.locator('.ant-pro-query-filter-collapse-button, a:has-text("展开")')
        if expand_btn.count() > 0:
            expand_btn.first.click(force=True)
            self.page.wait_for_timeout(1000)

    def fill_search(self, keyword: str, value: str):
        self.expand_filters()
        self.page.wait_for_timeout(500)
        inp = self.page.locator("#contractNumber")
        if inp.count() == 0:
            raise AssertionError("未找到 #contractNumber 输入框")
        inp.first.fill(value, force=True)
        self.page.wait_for_timeout(300)

    def click_reset(self):
        btns = self.page.locator("button")
        btns.nth(2).click(force=True)
        self.page.wait_for_timeout(1000)

    def click_query(self):
        btns = self.page.locator("button")
        btns.nth(3).click(force=True)
        _safe_networkidle(self.page)
        self.page.wait_for_timeout(2000)

    # ── 表格 ─────────────────────────────────────────────────

    def get_table_row_count(self) -> int:
        rows = self.page.locator(".ant-table-tbody tr.ant-table-row")
        return rows.count()

    def get_total_rows_hint(self) -> str:
        el = self.page.locator(".ant-pagination-total-text, .ant-pagination")
        if el.count() > 0:
            return el.first.inner_text().strip()
        return ""

    def click_pagination(self, page_num: int):
        link = self.page.locator(f'.ant-pagination-item a:text-is("{page_num}")')
        if link.count() > 0:
            link.first.click(force=True)
            _safe_networkidle(self.page)
            self.page.wait_for_timeout(1500)
        else:
            raise AssertionError(f"未找到页码 {page_num}")

    def get_all_rows_data(self) -> list[dict]:
        headers = self.page.locator(".ant-table-thead th")
        header_list = []
        for i in range(headers.count()):
            try:
                header_list.append(headers.nth(i).inner_text().strip())
            except Exception:
                header_list.append("")
        if not header_list:
            return []

        rows = self.page.locator(".ant-table-tbody tr.ant-table-row")
        result = []
        for i in range(rows.count()):
            try:
                cells = rows.nth(i).locator("td").all()
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

    def get_row_contract_no(self, row_index: int = 0) -> str:
        """获取指定行的合同编号"""
        rows = self.page.locator(".ant-table-tbody tr.ant-table-row")
        if row_index >= rows.count():
            return ""
        first_cell = rows.nth(row_index).locator("td").first
        return first_cell.inner_text().strip()

    # ── 新增合同 ─────────────────────────────────────────────

    def click_new_contract(self):
        """点击新增合同按钮"""
        btns = self.page.locator("button")
        if btns.count() <= 5:
            raise AssertionError(f"按钮数量不足（{btns.count()}），无法点击 button[5]")
        btn = btns.nth(5)
        btn_text = btn.inner_text().strip()
        if "新增" not in btn_text and "合同" not in btn_text:
            raise AssertionError(f"button[5] 不是新增合同按钮（当前文本: {btn_text}）")
        btn.click(force=True)
        self.page.wait_for_timeout(2000)

    def is_modal_visible(self) -> bool:
        modal = self.page.locator(".ant-modal")
        if modal.count() == 0:
            return False
        try:
            return modal.first.is_visible()
        except Exception:
            return False

    def is_drawer_visible(self) -> bool:
        drawer = self.page.locator(".ant-drawer")
        if drawer.count() == 0:
            return False
        try:
            return drawer.first.is_visible()
        except Exception:
            return False

    # ── 新增/编辑弹窗字段填写 ─────────────────────────────────────

    def fill_contract_name(self, name: str, in_modal: bool = True):
        """填写合同名称"""
        container = self.page.locator(".ant-modal") if in_modal else self.page
        inp = container.locator("input[placeholder='请输入合同名称']")
        if inp.count() == 0:
            # 尝试按 label 定位
            inp = container.locator(".ant-form-item:has-text('合同名称') input")
        inp.first.fill(name, force=True)
        self.page.wait_for_timeout(300)

    def fill_contract_amount(self, amount: str, in_modal: bool = True):
        """填写合同金额"""
        container = self.page.locator(".ant-modal") if in_modal else self.page
        inp = container.locator("input[placeholder='请输入合同金额']")
        if inp.count() == 0:
            inp = container.locator(".ant-form-item:has-text('合同金额') input")
        inp.first.fill(amount, force=True)
        self.page.wait_for_timeout(300)

    def select_dropdown_by_label(self, label: str, option_text: str, in_modal: bool = True):
        """根据 label 选择下拉选项"""
        container = self.page.locator(".ant-modal") if in_modal else self.page
        # 找到 label 对应的 select
        select = container.locator(f".ant-form-item:has-text('{label}') .ant-select")
        if select.count() == 0:
            raise AssertionError(f"未找到 {label} 对应的下拉框")
        select.first.click(force=True)
        self.page.wait_for_timeout(500)
        # 点击下拉选项
        option = self.page.locator(f".ant-select-dropdown:visible .ant-select-item:has-text('{option_text}')")
        if option.count() == 0:
            raise AssertionError(f"未找到下拉选项: {option_text}")
        option.first.click(force=True)
        self.page.wait_for_timeout(500)

    def fill_contract_date(self, date_str: str, in_modal: bool = True):
        """填写合同签订日期 (YYYY-MM-DD)"""
        container = self.page.locator(".ant-modal") if in_modal else self.page
        picker = container.locator(".ant-picker:has(input[placeholder='请选择合同签订日期'])")
        if picker.count() == 0:
            picker = container.locator(".ant-form-item:has-text('合同签订日期') .ant-picker")
        picker.first.click(force=True)
        self.page.wait_for_timeout(500)
        # 直接输入日期
        inp = picker.first.locator("input")
        inp.fill(date_str, force=True)
        self.page.wait_for_timeout(300)
        # 按 Enter 确认
        inp.press("Enter")
        self.page.wait_for_timeout(500)

    def fill_contract_period(self, start_date: str, end_date: str, in_modal: bool = True):
        """填写合同期限（日期范围）"""
        container = self.page.locator(".ant-modal") if in_modal else self.page
        picker = container.locator(".ant-picker-range:has(input[placeholder='请选择合同期限'])")
        if picker.count() == 0:
            picker = container.locator(".ant-form-item:has-text('合同期限') .ant-picker-range")
        picker.first.click(force=True)
        self.page.wait_for_timeout(500)
        # 输入开始日期
        inputs = picker.first.locator("input").all()
        if len(inputs) >= 2:
            inputs[0].fill(start_date, force=True)
            self.page.wait_for_timeout(300)
            inputs[1].fill(end_date, force=True)
            self.page.wait_for_timeout(300)
            inputs[1].press("Enter")
        self.page.wait_for_timeout(500)

    def fill_contract_remark(self, remark: str, in_modal: bool = True):
        """填写备注"""
        container = self.page.locator(".ant-modal") if in_modal else self.page
        # 备注可能是 textarea 或 input
        inp = container.locator(".ant-form-item:has-text('备注') textarea, .ant-form-item:has-text('备注') input")
        if inp.count() == 0:
            return
        inp.first.fill(remark, force=True)
        self.page.wait_for_timeout(300)

    # ── 弹窗操作 ─────────────────────────────────────────────

    def click_modal_button(self, text_keyword: str):
        btns = self.page.locator(".ant-modal button")
        for i in range(btns.count()):
            txt = btns.nth(i).inner_text().strip()
            if text_keyword in txt:
                btns.nth(i).click(force=True)
                self.page.wait_for_timeout(1000)
                return
        raise AssertionError(f"未找到弹窗中包含 '{text_keyword}' 的按钮")

    def click_modal_submit(self):
        """点击弹窗的确定/提交按钮"""
        for kw in ["确 定", "确 定", "提交", "保 存", "保 存"]:
            try:
                self.click_modal_button(kw)
                return
            except AssertionError:
                pass
        raise AssertionError("未找到确定/提交按钮")

    def close_modal(self):
        try:
            close_btn = self.page.locator(".ant-modal-close")
            if close_btn.count() > 0:
                close_btn.first.click(force=True)
                self.page.wait_for_timeout(1000)
                return
        except Exception:
            pass
        self.click_modal_button("取消")

    # ── 详情抽屉 ─────────────────────────────────────────────

    def click_detail_link(self, row_index: int = 0):
        """点击查看详情"""
        rows = self.page.locator(".ant-table-tbody tr.ant-table-row")
        if row_index >= rows.count():
            raise AssertionError(f"行索引 {row_index} 超出范围（共 {rows.count()} 行）")
        detail_span = rows.nth(row_index).locator("td").last.locator("span.primary, span[class*='pointer']")
        if detail_span.count() == 0:
            raise AssertionError(f"第 {row_index} 行未找到查看详情按钮")
        detail_span.first.click(force=True)
        self.page.wait_for_timeout(2000)

    def is_drawer_open(self) -> bool:
        return self.is_drawer_visible()

    def close_drawer(self):
        close_btn = self.page.locator(".ant-drawer-close")
        if close_btn.count() > 0:
            close_btn.first.click(force=True)
            self.page.wait_for_timeout(1000)

    # ── 编辑合同 ─────────────────────────────────────────────

    def click_edit_button(self):
        """在详情抽屉中点击编辑按钮"""
        edit_btn = self.page.locator("button:has-text('编 辑')")
        if edit_btn.count() == 0:
            edit_btn = self.page.locator("button:has-text('编辑')")
        if edit_btn.count() == 0:
            raise AssertionError("未找到编辑按钮")
        edit_btn.first.click(force=True)
        self.page.wait_for_timeout(2000)

    # ── 删除合同 ─────────────────────────────────────────────

    def click_delete_button(self):
        """在详情抽屉中点击删除按钮"""
        delete_btn = self.page.locator("button:has-text('删 除')")
        if delete_btn.count() == 0:
            delete_btn = self.page.locator("button:has-text('删除')")
        if delete_btn.count() == 0:
            raise AssertionError("未找到删除按钮")
        delete_btn.first.click(force=True)
        self.page.wait_for_timeout(1500)

    def confirm_delete(self, confirm: bool = True):
        """确认或取消删除"""
        if confirm:
            confirm_btn = self.page.locator(".ant-popconfirm .ant-btn-primary, .ant-modal-confirm .ant-btn-primary")
            if confirm_btn.count() > 0:
                confirm_btn.first.click(force=True)
                self.page.wait_for_timeout(2000)
        else:
            cancel_btn = self.page.locator(".ant-popconfirm .ant-btn:has-text('取消'), .ant-modal-confirm .ant-btn:has-text('取消')")
            if cancel_btn.count() > 0:
                cancel_btn.first.click(force=True)
                self.page.wait_for_timeout(1000)

    def is_popconfirm_visible(self) -> bool:
        popconfirm = self.page.locator(".ant-popconfirm:visible, .ant-modal-confirm:visible")
        return popconfirm.count() > 0

    # ── 等待操作结果 ─────────────────────────────────────────

    def wait_for_success_toast(self, timeout: int = 5000) -> bool:
        """等待成功提示"""
        try:
            toast = self.page.locator(".ant-message-success, .ant-notification-success")
            toast.first.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def wait_for_error_toast(self, timeout: int = 5000) -> bool:
        """等待错误提示"""
        try:
            toast = self.page.locator(".ant-message-error, .ant-notification-error")
            toast.first.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False
