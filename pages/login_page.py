"""
LoginPage — 登录页面对象
封装所有登录页的 UI 交互，与测试用例解耦。
"""
import time
from playwright.sync_api import Page, Locator


class LoginPage:
    """登录页面对象（Page Object）"""

    # ── 页面地址 ──────────────────────────────────────────────
    URL = "https://test6688.jh119.cn/business/#/login"

    # ── 元素定位器 ──────────────────────────────────────────────
    def __init__(self, page: Page):
        self.page = page

    # ── 基础操作 ──────────────────────────────────────────────

    @staticmethod
    def _safe_networkidle(page, timeout=5000):
        """等待 networkidle，超时后降级为 domcontentloaded（防止无头模式卡死）"""
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=3000)
            except Exception:
                pass

    def goto(self, clear_cookies: bool = True):
        """
        访问登录页
        - clear_cookies=True  （默认）每次访问都清 Cookie，从干净状态开始
        - clear_cookies=False  保留当前 context 的 Cookie，用于测试 session 持久化
        """
        if clear_cookies:
            self.page.context.clear_cookies()
        self.page.goto(self.URL, wait_until="domcontentloaded")
        self._safe_networkidle(self.page)
        self.page.wait_for_timeout(2000)

    def fill_phone(self, phone: str):
        """填写手机号"""
        self.page.locator("input").nth(0).fill(phone)
        self.page.wait_for_timeout(300)

    def fill_code(self, code: str):
        """填写验证码"""
        self.page.locator("input").nth(1).fill(code)
        self.page.wait_for_timeout(300)

    def click_get_code(self):
        """点击'获取验证码'按钮"""
        self.page.locator("button").nth(0).click()
        self.page.wait_for_timeout(500)

    def get_code_button_text(self) -> str:
        """获取'获取验证码'按钮的当前文字（用于判断倒计时）"""
        return self.page.locator("button").nth(0).inner_text(timeout=3000)

    def get_code_button_disabled(self) -> bool:
        """判断'获取验证码'按钮是否禁用"""
        btn = self.page.locator("button").nth(0)
        # ant-design 的 disabled 属性或 class
        return btn.is_disabled() or "disabled" in btn.get_attribute("class", "")

    def get_phone_input_value(self) -> str:
        """获取手机号输入框的值"""
        return self.page.locator("input").nth(0).input_value()

    def get_code_input_value(self) -> str:
        """获取验证码输入框的值"""
        return self.page.locator("input").nth(1).input_value()

    def get_error_tips(self) -> str:
        """获取页面上的错误提示文字（ant-form 提示）"""
        selectors = [
            ".ant-form-item-explain-error",
            ".ant-form-explain",
            "[class*='error']",
            "[class*='ant-message-error']",
        ]
        for sel in selectors:
            el = self.page.locator(sel).first
            if el.count() > 0 and el.is_visible(timeout=1000):
                return el.inner_text()
        return ""

    def has_error_tips(self) -> bool:
        """是否有错误提示"""
        return bool(self.get_error_tips())

    def get_page_inputs_count(self) -> int:
        """获取页面 input 元素数量"""
        return self.page.locator("input").count()

    def get_page_buttons_count(self) -> int:
        """获取页面 button 元素数量"""
        return self.page.locator("button").count()

    def click_submit_button(self):
        """直接点击'登 录'按钮（而非按 Enter），最多等 15 秒"""
        self.page.locator("button").nth(1).click(force=True)
        self.page.wait_for_timeout(3000)
        if "#/login" not in self.page.url:
            return
        for _ in range(12):
            time.sleep(1)
            if "#/login" not in self.page.url:
                return

    def submit(self):
        """提交登录，等待 URL 变化（跳离 /login 表示登录成功）。最多等 15 秒。"""
        self.page.locator("input").nth(1).press("Enter")
        # 用 Playwright wait_for_url 代替 time.sleep，pytest-timeout 可以中断。
        # !#/login 不是有效否定语法，改用 JS 判断：等待 URL 不再包含 #/login。
        try:
            self.page.wait_for_function(
                "() => !window.location.hash.includes('#/login')",
                timeout=15000,
            )
        except Exception:
            # 超时说明仍在 login 页（登录失败），继续往下走
            pass

    # ── 提交后处理 ──────────────────────────────────────────────

    def handle_after_submit(self):
        """
        统一处理提交后的所有可能 UI 阻塞：
        1. 尝试点"进入该单位"按钮（Modal 可能挡住它，force 可穿透）
        2. 尝试关 Modal
        3. 再点一次"进入该单位"（Modal 关掉后可能露出）
        4. 再关一次 Modal
        """
        # 1. 先尝试点按钮
        self._try_click_unit_button()

        # 2. 关闭 Modal（最多两轮）
        self._dismiss_modal()
        self._dismiss_modal()

        # 3. Modal 关掉后，再次尝试点"进入该单位"
        self._try_click_unit_button()

    def _try_click_unit_button(self):
        """尝试点击'进入该单位'按钮（force，覆盖 Modal 遮挡）"""
        try:
            btn = self.page.locator("button:has-text('进入该单位')")
            if btn.count() > 0:
                btn.first.click(force=True)
                self.page.wait_for_timeout(2000)
        except Exception:
            pass

    def _dismiss_modal(self):
        """关闭 ant-design Modal"""
        self.page.wait_for_timeout(1000)
        try:
            if self.page.locator(".ant-modal-wrap").count() > 0:
                # 优先找右上角关闭按钮
                x_btn = self.page.locator(".ant-modal-close, .ant-modal-close-x").first
                if x_btn.count() > 0:
                    x_btn.click(force=True)
                else:
                    # 点 Modal 里的第一个按钮
                    self.page.locator(".ant-modal button").first.click(force=True)
                self.page.wait_for_timeout(1500)
        except Exception:
            pass

    # ── 状态判断 ──────────────────────────────────────────────

    def is_at_login_page(self) -> bool:
        """判断是否仍在登录页"""
        return "#/login" in self.page.url

    def is_logged_in(self) -> bool:
        """判断是否已登录（不在登录页即为登录成功）"""
        return "#/login" not in self.page.url

    # ── 登出 ──────────────────────────────────────────────

    def logout(self):
        """
        从登录态登出：
        1. 点击右上角头像 → 弹出菜单
        2. 点击'退出登陆'
        """
        # 点击头像打开菜单
        avatar_selectors = [
            "[class*='avatar']",
            "[class*='userName']",
            "[class*='user-name']",
            ".avatar",
            ".user-info",
            "[class*='header-user']",
            "img[class*='avatar']",
            ".user-avatar",
        ]
        for sel in avatar_selectors:
            try:
                el = self.page.locator(sel).first
                if el.is_visible(timeout=3000):
                    el.click()
                    self.page.wait_for_timeout(1000)
                    break
            except Exception:
                continue

        # 在菜单里找"退出登陆"或"退出"
        logout_selectors = [
            "button:has-text('退出登陆')",
            "a:has-text('退出登陆')",
            "span:has-text('退出登陆')",
            "button:has-text('退出')",
            "a:has-text('退出')",
            "[class*='logout']",
            "[class*='signout']",
        ]
        for sel in logout_selectors:
            try:
                el = self.page.locator(sel).first
                if el.is_visible(timeout=2000):
                    el.click()
                    self.page.wait_for_timeout(2000)
                    return True
            except Exception:
                continue
        return False

    # ── 截图 ──────────────────────────────────────────────

    def screenshot(self, path: str):
        """页面截图（调试用）"""
        self.page.screenshot(path=path)
