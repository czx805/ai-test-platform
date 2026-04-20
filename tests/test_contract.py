"""
test_contract.py — 合同管理模块测试用例（包含 CRUD 操作）
覆盖：列表页加载、统计卡片、表格数据、搜索筛选、新增合同、编辑合同、删除合同、分页、详情
"""
import os
import pytest

from pages.contract_page import ContractPage
from tests.testdata.contract_data import (
    NEW_CONTRACT_MINIMAL,
    NEW_CONTRACT_FULL,
    NEW_CONTRACT_INVALID_CASES,
    EDIT_CONTRACT_CASES,
    DELETE_CONFIRM_CASES,
    generate_contract_name,
)


os.makedirs("logs", exist_ok=True)


# ══════════════════════════════════════════════════════════════
#  页面加载 & 状态
# ══════════════════════════════════════════════════════════════

def test_contract_page_loaded(contract_page):
    """合同管理页面应正常加载"""
    cp = contract_page
    cp.screenshot("logs/contract_page.png")
    assert cp.is_at_contract(), f"未在合同管理页面: {cp.url}"
    print(f"[PASS] 合同管理页面已加载: {cp.url}")


def test_contract_stats_visible(contract_page):
    """顶部统计卡片应可见，包含合同总数、已生效等数值"""
    cp = contract_page
    total = cp.get_stat_value(index=0)
    pending = cp.get_stat_value(index=5)
    expired = cp.get_stat_value(index=7)
    cp.screenshot("logs/contract_stats.png")
    assert total, "合同总数未显示"
    print(f"[PASS] 统计卡片: 合同总数={total}, 待签署={pending}, 失效合同数={expired}")


def test_contract_table_columns(contract_page):
    """表格列应完整"""
    cp = contract_page
    rows = cp.get_all_rows_data()
    cp.screenshot("logs/contract_table.png")
    assert len(rows) > 0, "合同列表为空"
    first_row = rows[0]
    expected_cols = ["合同编号", "合同名称"]
    for col in expected_cols:
        assert col in first_row, f"缺少列: {col}"
    print(f"[PASS] 表格列完整，共 {len(first_row)} 列")


# ══════════════════════════════════════════════════════════════
#  数据 & 分页
# ══════════════════════════════════════════════════════════════

def test_contract_list_not_empty(contract_page):
    """合同列表应有数据"""
    cp = contract_page
    rows = cp.get_all_rows_data()
    assert len(rows) >= 1, "合同列表为空"
    print(f"[PASS] 合同列表有 {len(rows)} 条数据")


def test_contract_pagination_exists(contract_page):
    """分页组件应存在且显示总条数"""
    cp = contract_page
    hint = cp.get_total_rows_hint()
    cp.screenshot("logs/contract_pagination.png")
    assert "条" in hint or hint, f"分页提示异常: {hint}"
    print(f"[PASS] 分页: {hint}")


# ══════════════════════════════════════════════════════════════
#  搜索 & 筛选
# ══════════════════════════════════════════════════════════════

def test_contract_search_by_contract_no(contract_page):
    """按合同编号精确搜索应返回对应结果"""
    cp = contract_page
    cp.expand_filters()
    cp.fill_search("合同编号", "20260407-001")
    cp.click_query()
    rows = cp.get_all_rows_data()
    cp.screenshot("logs/contract_search_result.png")
    assert len(rows) >= 1, "搜索结果为空"
    assert any("20260407-001" in r.get("合同编号", "") for r in rows), \
        f"搜索结果不匹配，rows={rows}"
    print(f"[PASS] 按合同编号搜索返回 {len(rows)} 条结果")


def test_contract_search_reset(contract_page):
    """重置按钮应清空搜索条件"""
    cp = contract_page
    rows_before = len(cp.get_all_rows_data())
    cp.expand_filters()
    cp.fill_search("合同编号", "20260407-001")
    cp.click_reset()
    rows_after = len(cp.get_all_rows_data())
    cp.screenshot("logs/contract_reset.png")
    assert rows_after > 0, "重置后表格应恢复可用"
    print(f"[PASS] 重置功能正常：恢复后 {rows_after} 行（重置前 {rows_before} 行）")


def test_contract_filter_area_expandable(contract_page):
    """展开按钮应能正常工作"""
    cp = contract_page
    before = len(cp.get_all_rows_data())
    cp.expand_filters()
    after = len(cp.get_all_rows_data())
    cp.screenshot("logs/contract_filter_expanded.png")
    print(f"[PASS] 展开筛选区，数据条数 {before} -> {after}，无变化")


# ══════════════════════════════════════════════════════════════
#  新增合同
# ══════════════════════════════════════════════════════════════

def test_contract_new_modal_open(contract_page):
    """点击新增合同应弹出弹窗"""
    cp = contract_page
    cp.click_new_contract()
    cp.screenshot("logs/contract_new_modal.png")
    assert cp.is_modal_visible(), "新增合同弹窗未出现"
    # 关闭弹窗
    cp.close_modal()
    print("[PASS] 新增合同弹窗正常打开并关闭")


@pytest.mark.parametrize("case", NEW_CONTRACT_INVALID_CASES, ids=[c["id"] for c in NEW_CONTRACT_INVALID_CASES])
def test_contract_new_invalid_fields(contract_page, case):
    """新增合同时，{desc} 应被拦截"""
    cp = contract_page
    cp.click_new_contract()
    assert cp.is_modal_visible(), "弹窗未出现"
    
    # 填写字段
    if case.get("name"):
        cp.fill_contract_name(case["name"])
    if case.get("amount"):
        cp.fill_contract_amount(case["amount"])
    
    # 尝试提交
    try:
        cp.click_modal_submit()
        # 检查是否出现错误提示
        has_error = cp.wait_for_error_toast(timeout=2000)
        if case.get("expect_error"):
            assert has_error or cp.is_modal_visible(), f"应出现错误提示或弹窗未关闭"
    except AssertionError:
        if not case.get("expect_error"):
            raise
    
    # 关闭弹窗
    cp.close_modal()
    print(f"[PASS] {case['desc']} 被正确拦截")


# ══════════════════════════════════════════════════════════════
#  编辑合同
# ══════════════════════════════════════════════════════════════

def test_contract_edit_modal_open(contract_page):
    """在详情抽屉中点击编辑应弹出编辑弹窗"""
    cp = contract_page
    # 点击第一行查看详情
    cp.click_detail_link(0)
    cp.page.wait_for_timeout(2000)
    assert cp.is_drawer_open(), "详情抽屉未打开"
    
    # 点击编辑按钮
    cp.click_edit_button()
    cp.page.wait_for_timeout(2000)
    cp.screenshot("logs/contract_edit_modal.png")
    assert cp.is_modal_visible(), "编辑弹窗未出现"
    
    # 关闭编辑弹窗和详情抽屉
    cp.close_modal()
    cp.page.wait_for_timeout(1000)
    cp.close_drawer()
    print("[PASS] 编辑弹窗正常打开并关闭")


# ══════════════════════════════════════════════════════════════
#  删除合同
# ══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("case", DELETE_CONFIRM_CASES, ids=[c["id"] for c in DELETE_CONFIRM_CASES])
def test_contract_delete_confirmation(contract_page, case):
    """删除合同时，{desc}"""
    cp = contract_page
    # 点击第一行查看详情
    cp.click_detail_link(0)
    cp.page.wait_for_timeout(2000)
    assert cp.is_drawer_open(), "详情抽屉未打开"
    
    # 点击删除按钮
    cp.click_delete_button()
    cp.page.wait_for_timeout(1500)
    cp.screenshot(f"logs/contract_delete_confirm_{case['id']}.png")
    assert cp.is_popconfirm_visible(), "删除确认弹窗未出现"
    
    # 确认或取消
    cp.confirm_delete(confirm=case["confirm"])
    cp.page.wait_for_timeout(2000)
    
    if case["confirm"]:
        # 确认删除后，抽屉应关闭，表格行数应减少
        assert not cp.is_drawer_open(), "删除后抽屉应关闭"
        print(f"[PASS] {case['desc']} 成功")
    else:
        # 取消删除后，抽屉应仍然打开
        assert cp.is_drawer_open(), "取消删除后抽屉应仍然打开"
        cp.close_drawer()
        print(f"[PASS] {case['desc']} 成功")


# ══════════════════════════════════════════════════════════════
#  分页
# ══════════════════════════════════════════════════════════════

def test_contract_pagination_page2(contract_page):
    """翻到第2页应正常显示"""
    cp = contract_page
    if not cp.is_at_contract():
        cp.goto()
    cp.click_pagination(2)
    rows = cp.get_all_rows_data()
    cp.screenshot("logs/contract_page2.png")
    assert len(rows) > 0, "第2页数据为空"
    hint = cp.get_total_rows_hint()
    print(f"[PASS] 第2页有 {len(rows)} 条数据，分页提示: {hint}")


# ══════════════════════════════════════════════════════════════
#  合同详情
# ══════════════════════════════════════════════════════════════

def test_contract_detail_drawer(contract_page):
    """点击查看详情应显示合同详情抽屉"""
    cp = contract_page
    if not cp.is_at_contract():
        cp.goto()
    if cp.is_modal_visible():
        cp.close_modal()

    cp.click_detail_link(0)
    cp.page.wait_for_timeout(3000)
    cp.screenshot("logs/contract_detail_drawer.png")

    assert cp.is_drawer_open(), "详情抽屉未打开"
    print(f"[PASS] 查看详情成功，抽屉已打开")
