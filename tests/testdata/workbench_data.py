# testdata/workbench_data.py — 工作台模块测试数据

from pages.workbench_page import WorkbenchPage

# ── 导航项检查数据 ──────────────────────────────────────
# 核心导航项（必须在侧边栏可见）
CORE_NAV_ITEMS = [
    {"key": "workbench",     "name": "工作台"},
    {"key": "project",       "name": "项目管理"},
    {"key": "contract",      "name": "合同管理"},
    {"key": "task",          "name": "任务管理"},
]

# 全部导航项（用于完整性检查）
ALL_NAV_ITEMS = [
    {"key": k, "name": v["name"]}
    for k, v in WorkbenchPage.NAV_ITEMS.items()
]

# ── 导航跳转验证数据 ──────────────────────────────────────
# 点击导航项后应跳转到的 URL 片段
NAV_CLICK_CASES = [
    {"key": "project",       "expected_url": "#/project",          "name": "项目管理"},
    {"key": "unitInfo",      "expected_url": "#/unitInfo",         "name": "单位管理"},
    {"key": "contract",      "expected_url": "#/contract",         "name": "合同管理"},
    {"key": "task",          "expected_url": "#/task",             "name": "任务管理"},
    {"key": "statistics",    "expected_url": "#/statistics",       "name": "数据统计"},
]
