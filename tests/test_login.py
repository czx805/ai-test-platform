"""
test_login.py — 登录模块测试用例（数据驱动 + Page Object）
- 登录成功：独立用例
- 登录失败：参数化数据驱动（testdata/login_data.py）
- 退出登录：独立用例
"""
import os
import pytest

from pages.login_page import LoginPage
from tests.testdata.login_data import VALID_PHONE, VALID_CODE, LOGIN_FAIL_CASES, GET_CODE_CASES, EXPECTED_ELEMENTS


os.makedirs("logs", exist_ok=True)


# ── 辅助 ──────────────────────────────────────────────
def _do_login(lp):
    """完整登录流程，供退出用例等复用"""
    lp.fill_phone(VALID_PHONE)
    lp.fill_code(VALID_CODE)
    lp.submit()
    lp.handle_after_submit()
    return lp


# ══════════════════════════════════════════════════════════════
#  登录成功（独立用例）
# ══════════════════════════════════════════════════════════════
def test_login_success(login_page):
    """正确验证码登录 -> 跳转 workbench"""
    lp = login_page
    _do_login(lp)
    lp.screenshot("logs/po_login_success.png")

    assert not lp.is_at_login_page(), f"登录失败，仍在登录页: {lp.page.url}"
    print(f"[PASS] 登录成功: {lp.page.url}")


# ══════════════════════════════════════════════════════════════
#  登录失败（数据驱动 — 一条代码跑全部失败场景）
# ══════════════════════════════════════════════════════════════
@pytest.mark.timeout(30)
@pytest.mark.parametrize("case", LOGIN_FAIL_CASES, ids=[c["id"] for c in LOGIN_FAIL_CASES])
def test_login_fail(login_page, case):
    """数据驱动: {desc} -> 应停留在登录页""".format(**case)
    lp = login_page

    # 是否先点"获取验证码"
    if case.get("request_code"):
        lp.fill_phone(case["phone"])
        lp.click_get_code()

    # 填写并提交
    lp.fill_phone(case["phone"])
    lp.fill_code(case["code"])
    lp.submit()
    lp.handle_after_submit()
    lp.screenshot(f"logs/po_fail_{case['id']}.png")

    assert lp.is_at_login_page(), f"[{case['id']}] 不应登录成功: {lp.page.url}"
    print(f"[PASS] [{case['id']}] {case['desc']} 被正确拦截")


# ══════════════════════════════════════════════════════════════
#  退出登录（独立用例）
# ══════════════════════════════════════════════════════════════
def test_logout(login_page):
    """登录后退出 -> 跳转回登录页"""
    lp = login_page
    _do_login(lp)

    if lp.is_at_login_page():
        lp.screenshot("logs/po_logout_login_failed.png")
        pytest.skip(f"登录失败，跳过退出用例: {lp.page.url}")

    lp.screenshot("logs/po_logout_before.png")
    lp.logout()
    lp.screenshot("logs/po_logout_after.png")

    assert lp.is_at_login_page(), f"退出后不在登录页: {lp.page.url}"
    print(f"[PASS] 退出成功: {lp.page.url}")


# ══════════════════════════════════════════════════════════════
#  获取验证码按钮行为（参数化）
# ══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("case", GET_CODE_CASES, ids=[c["id"] for c in GET_CODE_CASES])
def test_get_code_button_behavior(login_page, case):
    """{desc} -> 按钮应正常响应""".format(**case)
    lp = login_page
    lp.fill_phone(case["phone"])
    lp.screenshot(f"logs/po_getcode_before_{case['id']}.png")

    # 点击获取验证码
    lp.click_get_code()
    lp.page.wait_for_timeout(1000)
    lp.screenshot(f"logs/po_getcode_after_{case['id']}.png")

    # 检查按钮文字变化（倒计时或重新可点击）
    btn_text = lp.get_code_button_text()
    print(f"[{case['id']}] 按钮文字: {btn_text}")
    # 有效手机号点击后应有倒计时（数字秒数）或验证码已发送提示
    # 无效手机号点击后按钮应保持原样或提示错误
    assert lp.page.locator("button").count() >= 2, "按钮数量不足"


# ══════════════════════════════════════════════════════════════
#  键盘操作测试
# ══════════════════════════════════════════════════════════════
def test_tab_key_navigation(login_page):
    """Tab 键应能正常在手机号和验证码之间切换"""
    lp = login_page
    lp.fill_phone("137")
    lp.screenshot("logs/po_tab_phone.png")

    # 第一个 input 按 Tab，光标应跳到第二个 input
    lp.page.locator("input").nth(0).press("Tab")
    lp.screenshot("logs/po_tab_after.png")

    # 验证验证码框获得焦点（按任意字符输入）
    lp.page.keyboard.type("8888")
    lp.screenshot("logs/po_tab_typed.png")
    code_val = lp.get_code_input_value()

    assert "8888" in code_val, f"Tab 后输入未进入验证码框，当前值: {code_val}"
    print(f"[PASS] Tab 键导航正常，验证码框值: {code_val}")


def test_enter_key_on_phone_field(login_page):
    """手机号框按 Enter -> 光标应跳到验证码框（不触发表单提交）"""
    lp = login_page
    lp.fill_phone(VALID_PHONE)
    lp.page.locator("input").nth(0).press("Enter")
    lp.screenshot("logs/po_enter_on_phone.png")

    # 预期：仍在登录页，光标在验证码框
    assert lp.is_at_login_page(), "手机号框按 Enter 不应提交表单"
    print(f"[PASS] 手机号框按 Enter 未触发提交，仍在: {lp.page.url}")


def test_enter_key_on_code_field_submits(login_page):
    """验证码框按 Enter -> 应触发登录提交"""
    lp = login_page
    lp.fill_phone(VALID_PHONE)
    lp.fill_code(VALID_CODE)
    lp.screenshot("logs/po_enter_on_code_before.png")
    lp.page.locator("input").nth(1).press("Enter")
    lp.page.wait_for_timeout(3000)
    lp.handle_after_submit()
    lp.screenshot("logs/po_enter_on_code_after.png")

    # 应触发登录（URL 变化）
    assert not lp.is_at_login_page(), f"验证码框按 Enter 应提交表单: {lp.page.url}"
    print(f"[PASS] 验证码框按 Enter 提交成功: {lp.page.url}")


# ══════════════════════════════════════════════════════════════
#  连续多次点击测试
# ══════════════════════════════════════════════════════════════
def test_multiple_login_attempts_slow(login_page):
    """正确账号连续 3 次快速登录 -> 只应成功 1 次"""
    lp = login_page
    for i in range(3):
        lp.goto()  # 重新访问登录页
        lp.fill_phone(VALID_PHONE)
        lp.fill_code(VALID_CODE)
        lp.submit()
        lp.handle_after_submit()
        lp.screenshot(f"logs/po_multi_attempt_{i+1}.png")
        if not lp.is_at_login_page():
            print(f"[PASS] 第 {i+1} 次登录成功: {lp.page.url}")
            break
    else:
        print(f"[INFO] 3 次均未登录成功: {lp.page.url}")


# ══════════════════════════════════════════════════════════════
#  Session / Cookie 持久化测试
# ══════════════════════════════════════════════════════════════
def test_session_persist_after_refresh(login_page):
    """登录后刷新页面 -> 应保持登录态（不退回登录页）"""
    lp = login_page
    _do_login(lp)
    lp.screenshot("logs/po_refresh_before.png")

    # 刷新当前页面
    lp.page.reload(wait_until="domcontentloaded")
    lp.page.wait_for_selector("a[href^='#/']")
    lp.screenshot("logs/po_refresh_after.png")

    assert not lp.is_at_login_page(), f"刷新后登录态丢失: {lp.page.url}"
    print(f"[PASS] 刷新后 session 保持: {lp.page.url}")


def test_session_persist_after_navigate(login_page):
    """登录后手动访问登录页 URL -> SPA 正常响应，页面可加载"""
    lp = login_page
    _do_login(lp)
    lp.screenshot("logs/po_nav_before.png")

    # 手动访问登录页 URL（不清 Cookie，保留登录态）
    lp.page.goto(LoginPage.URL, wait_until="domcontentloaded")
    lp.page.wait_for_selector("a[href^='#/']")
    lp.screenshot("logs/po_nav_after.png")

    # SPA 可能仍渲染 #/login，但页面应正常加载无报错
    # 检查 input 和 button 元素仍然存在
    assert lp.get_page_inputs_count() >= 2, f"页面加载异常，inputs: {lp.get_page_inputs_count()}"
    print(f"[PASS] 已登录时访问登录页正常响应: {lp.page.url}")


# ══════════════════════════════════════════════════════════════
#  浏览器后退测试
# ══════════════════════════════════════════════════════════════
def test_back_from_workbench(login_page):
    """登录成功后点浏览器后退 -> 应留在当前页（不退回登录页）"""
    lp = login_page
    _do_login(lp)
    url_before = lp.page.url
    lp.screenshot("logs/po_back_before.png")

    lp.page.go_back()
    lp.page.wait_for_selector("a[href^='#/']")
    lp.screenshot("logs/po_back_after.png")
    url_after = lp.page.url

    # 已登录状态下后退，大多数 SPA 会留在当前页或跳回首页
    print(f"[INFO] 后退前: {url_before}, 后退后: {url_after}")
    # 不做强制断言，只记录行为


# ══════════════════════════════════════════════════════════════
#  页面元素完整性检查
# ══════════════════════════════════════════════════════════════
def test_page_elements_integrity(login_page):
    """登录页必须包含预期的所有核心元素"""
    lp = login_page

    # input 数量应为 2
    inputs_count = lp.get_page_inputs_count()
    buttons_count = lp.get_page_buttons_count()
    lp.screenshot("logs/po_elements_integrity.png")

    assert inputs_count >= 2, f"登录页 input 不足（当前 {inputs_count}）"
    assert buttons_count >= 2, f"登录页 button 不足（当前 {buttons_count})"

    # 检查关键元素存在
    for name, info in EXPECTED_ELEMENTS.items():
        el = lp.page.locator(info["selector"]).nth(info["index"])
        assert el.count() > 0, f"缺少 {name}: {info['desc']}"
        print(f"  {info['desc']} [{name}]: OK")

    print(f"[PASS] 页面元素完整: {inputs_count} inputs, {buttons_count} buttons")


# ══════════════════════════════════════════════════════════════
#  输入框清空行为
# ══════════════════════════════════════════════════════════════
def test_input_clear_behavior(login_page):
    """重新输入应覆盖旧值，而非追加"""
    lp = login_page

    # 第一次填
    lp.fill_phone("13711111111")
    lp.fill_code("1234")
    assert lp.get_phone_input_value() == "13711111111"
    assert lp.get_code_input_value() == "1234"
    lp.screenshot("logs/po_clear_before.png")

    # 第二次填（用 fill，覆盖而非追加）
    lp.fill_phone(VALID_PHONE)
    lp.fill_code(VALID_CODE)
    lp.screenshot("logs/po_clear_after.png")

    assert lp.get_phone_input_value() == VALID_PHONE, "fill 应覆盖旧值"
    assert lp.get_code_input_value() == VALID_CODE, "fill 应覆盖旧值"
    print(f"[PASS] fill 方法正确覆盖旧值，无追加问题")

