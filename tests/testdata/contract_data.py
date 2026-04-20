# testdata/contract_data.py — 合同管理模块测试数据

import time
from datetime import datetime, timedelta

# ── 测试合同数据生成器 ──────────────────────────────────────

def generate_contract_name(prefix: str = "自动化测试合同") -> str:
    """生成带时间戳的合同名称，避免重复"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{ts}"


def generate_contract_data(
    name_prefix: str = "自动化测试合同",
    amount: str = "10000",
    start_offset_days: int = 0,
    duration_days: int = 365,
) -> dict:
    """
    生成完整的合同数据字典
    
    Args:
        name_prefix: 合同名称前缀
        amount: 合同金额（字符串）
        start_offset_days: 合同开始日期距今天数（0=今天）
        duration_days: 合同有效天数
    
    Returns:
        dict: 包含所有合同字段的字典
    """
    today = datetime.now()
    start_date = today + timedelta(days=start_offset_days)
    end_date = start_date + timedelta(days=duration_days)
    
    return {
        "name": generate_contract_name(name_prefix),
        "amount": amount,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "remark": f"自动化测试创建于 {today.strftime('%Y-%m-%d %H:%M:%S')}",
    }


# ── 新增合同测试数据 ──────────────────────────────────────

# 最小必填字段（假设合同名称和金额是必填的）
NEW_CONTRACT_MINIMAL = generate_contract_data(
    name_prefix="最小字段合同",
    amount="5000",
)

# 完整字段
NEW_CONTRACT_FULL = generate_contract_data(
    name_prefix="完整字段合同",
    amount="88888",
    start_offset_days=7,
    duration_days=730,
)

# 边界值测试数据
NEW_CONTRACT_CASES = [
    {
        "id": "min_amount",
        "name_prefix": "最小金额合同",
        "amount": "0.01",
        "desc": "最小金额 0.01 元",
    },
    {
        "id": "max_amount",
        "name_prefix": "大额合同",
        "amount": "99999999.99",
        "desc": "大金额合同",
    },
    {
        "id": "long_name",
        "name_prefix": "这是一个非常长的合同名称用于测试系统对长文本的处理能力应该能够正常保存和显示",
        "amount": "1000",
        "desc": "长合同名称",
    },
]

# 无效数据（用于验证表单校验）
NEW_CONTRACT_INVALID_CASES = [
    {
        "id": "empty_name",
        "name": "",
        "amount": "1000",
        "desc": "合同名称为空",
        "expect_error": True,
    },
    {
        "id": "empty_amount",
        "name": generate_contract_name("空金额合同"),
        "amount": "",
        "desc": "合同金额为空",
        "expect_error": True,
    },
    {
        "id": "negative_amount",
        "name": generate_contract_name("负金额合同"),
        "amount": "-100",
        "desc": "负数金额",
        "expect_error": True,
    },
    {
        "id": "invalid_amount",
        "name": generate_contract_name("非法金额合同"),
        "amount": "abc",
        "desc": "非数字金额",
        "expect_error": True,
    },
]


# ── 编辑合同测试数据 ──────────────────────────────────────

EDIT_CONTRACT_CASES = [
    {
        "id": "edit_name",
        "new_name_prefix": "已修改合同名",
        "new_amount": None,
        "desc": "仅修改合同名称",
    },
    {
        "id": "edit_amount",
        "new_name_prefix": None,
        "new_amount": "20000",
        "desc": "仅修改合同金额",
    },
    {
        "id": "edit_both",
        "new_name_prefix": "完全修改合同",
        "new_amount": "30000",
        "desc": "同时修改名称和金额",
    },
]


# ── 删除确认测试数据 ──────────────────────────────────────

DELETE_CONFIRM_CASES = [
    {
        "id": "cancel_delete",
        "confirm": False,
        "desc": "取消删除操作",
    },
    {
        "id": "confirm_delete",
        "confirm": True,
        "desc": "确认删除操作",
    },
]
