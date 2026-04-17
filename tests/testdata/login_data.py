# testdata/login_data.py — 登录模块测试数据
# 所有测试参数集中管理，改数据不改代码

# ── 有效账号 ──────────────────────────────────────────────
VALID_PHONE = "13757188737"
VALID_CODE  = "8888"

# ── 登录失败参数化数据 ──────────────────────────────────────
# 格式: (用例ID, 手机号, 验证码, 是否点击获取验证码, 预期描述)
LOGIN_FAIL_CASES = [
    {
        "id": "wrong_code",
        "phone": VALID_PHONE,
        "code": "0000",
        "request_code": False,
        "desc": "错误验证码",
    },
    {
        "id": "empty_phone",
        "phone": "",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "空手机号",
    },
    {
        "id": "empty_code",
        "phone": VALID_PHONE,
        "code": "",
        "request_code": False,
        "desc": "空验证码",
    },
    {
        "id": "no_code_request",
        "phone": VALID_PHONE,
        "code": "",
        "request_code": False,
        "desc": "未获取验证码直接提交",
    },
    {
        "id": "short_phone",
        "phone": "138",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "手机号过短",
    },
    {
        "id": "invalid_phone_format",
        "phone": "abcdefghijk",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "手机号含字母",
    },
    {
        "id": "code_all_zero",
        "phone": VALID_PHONE,
        "code": "000000",
        "request_code": True,
        "desc": "验证码全零(6位)",
    },
    {
        "id": "code_too_short",
        "phone": VALID_PHONE,
        "code": "12",
        "request_code": False,
        "desc": "验证码位数不足",
    },
    {
        "id": "phone_with_spaces",
        "phone": "137 5718 8737",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "手机号含空格",
    },
    {
        "id": "phone_with_special_chars",
        "phone": "1375718873@",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "手机号含特殊字符",
    },
    {
        "id": "phone_11_zeros",
        "phone": "00000000000",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "手机号全零",
    },
    {
        "id": "phone_12_digits",
        "phone": "137571887370",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "手机号超长(12位)",
    },
    {
        "id": "phone_10_digits",
        "phone": "1375718873",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "手机号少一位(10位)",
    },
    {
        "id": "code_with_spaces",
        "phone": VALID_PHONE,
        "code": "88 88",
        "request_code": False,
        "desc": "验证码含空格",
    },
    {
        "id": "code_with_special_chars",
        "phone": VALID_PHONE,
        "code": "88@8",
        "request_code": False,
        "desc": "验证码含特殊字符",
    },
    {
        "id": "code_all_nine",
        "phone": VALID_PHONE,
        "code": "9999",
        "request_code": False,
        "desc": "验证码全9",
    },
    {
        "id": "both_empty",
        "phone": "",
        "code": "",
        "request_code": False,
        "desc": "手机号和验证码都为空",
    },
    {
        "id": "sql_injection_phone",
        "phone": "' OR 1=1 --",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "SQL注入手机号",
    },
    {
        "id": "xss_phone",
        "phone": "<script>alert(1)</script>",
        "code": VALID_CODE,
        "request_code": False,
        "desc": "XSS攻击手机号",
    },
]

# ── 获取验证码按钮参数化数据 ──────────────────────────────────────
GET_CODE_CASES = [
    {
        "id": "code_request_empty_phone",
        "phone": "",
        "desc": "空手机号获取验证码",
        "should_disable": True,  # 预期按钮不响应或被禁用
    },
    {
        "id": "code_request_short_phone",
        "phone": "138",
        "desc": "手机号过短获取验证码",
        "should_disable": True,
    },
    {
        "id": "code_request_valid_phone",
        "phone": VALID_PHONE,
        "desc": "有效手机号获取验证码",
        "should_disable": False,  # 预期按钮进入倒计时
    },
]

# ── 页面元素完整性检查 ──────────────────────────────────────
# 预期登录页应该存在的元素
EXPECTED_ELEMENTS = {
    "phone_input": {"selector": "input", "index": 0, "desc": "手机号输入框"},
    "code_input": {"selector": "input", "index": 1, "desc": "验证码输入框"},
    "get_code_btn": {"selector": "button", "index": 0, "desc": "获取验证码按钮"},
    "login_btn": {"selector": "button", "index": 1, "desc": "登录按钮"},
}
