# AI Test Platform — 自动化测试框架

基于 Python 3.11 + Playwright (sync) + pytest 的 Web UI 自动化测试框架。

---

## 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（首次）
python -m playwright install chromium
```

---

## 快速运行

```bash
# 激活虚拟环境
.\venvs\Scripts\activate

# 运行全部测试（97 用例，约 22 分钟）
pytest tests/ -q

# 只跑某个模块
pytest tests/test_contract.py -q

# 只跑单个用例
pytest tests/test_contract.py::test_contract_new_modal_open -v

# 跳过慢用例
pytest tests/ -q -m "not slow"

# Headless 模式（cron 任务自动使用）
$env:PLAYWRIGHT_HEADLESS="1"; pytest tests/ -q
```

---

## 测试报告

测试完成后自动生成两份报告：

| 报告 | 文件 | 说明 |
|------|------|------|
| 自定义中文报告 | `reports/report.html` | 精选样式，截图可放大 |
| pytest-html 报告 | `reports/html-report.html` | 标准格式，兼容 CI |

```bash
# 重新生成自定义报告
python generate_report.py
```

---

## 项目结构

```
ai-test-platform/
├── tests/               # 测试用例（按模块分文件）
│   ├── test_login.py    # 登录模块  33 用例
│   ├── test_workbench.py# 工作台模块 32 用例
│   ├── test_contract.py # 合同管理模块 18 用例（含 CRUD）
│   └── testdata/        # 测试数据
│       ├── login_data.py
│       ├── workbench_data.py
│       └── contract_data.py
├── pages/               # Page Object 页面对象
│   ├── login_page.py
│   ├── workbench_page.py
│   └── contract_page.py  # 支持新增、编辑、删除
├── conftest.py          # pytest fixtures + 报告钩子
├── pytest.ini           # pytest 配置（90s 超时）
├── generate_report.py   # 自定义报告生成器
├── auto_sync.py         # 定时任务脚本（钉钉通知）
├── requirements.txt     # 真实依赖（仅 5 个包）
├── logs/                # 截图和临时文件
└── reports/             # 测试报告输出目录
    ├── report.html      # 自定义中文 HTML 报告
    ├── report_data.json # 原始测试数据
    └── html-report.html # pytest-html 报告
```

---

## 合同管理模块测试覆盖

| 功能 | 用例数 | 覆盖场景 |
|------|--------|----------|
| 页面加载 | 3 | 页面加载、统计卡片、表格列 |
| 数据展示 | 2 | 列表非空、分页存在 |
| 搜索筛选 | 3 | 按编号搜索、重置、展开筛选 |
| 新增合同 | 5 | 弹窗打开、空名称、空金额、负数、非法字符 |
| 编辑合同 | 1 | 编辑弹窗打开 |
| 删除合同 | 2 | 取消删除、确认删除 |
| 分页 | 1 | 翻到第2页 |
| 详情 | 1 | 详情抽屉打开 |

---

## 测试账号

| 环境 | 地址 |
|------|------|
| 测试站点 | https://test6688.jh119.cn/business |
| 手机号 | 13757188737 |
| 验证码 | 8888 |

---

## 新增模块流程

1. **探索页面结构** — 写一个 `explore_xxx.py` 调试脚本，记录元素选择器
2. **编写测试数据** — `tests/testdata/xxx_data.py`，集中管理测试参数
3. **编写 Page Object** — `pages/xxx_page.py`，封装所有页面操作
4. **编写测试用例** — `tests/test_xxx.py`，使用 pytest fixtures
5. **注册 fixture** — 在 `conftest.py` 中添加 page object fixture
6. **运行验证** — `pytest tests/test_xxx.py -q`
7. **生成报告** — `python generate_report.py`

---

## 定时任务（本地 + GitHub 双通道）

项目已配置自动同步定时任务：

### 方式一：本地 Cron（依赖电脑开机）
- 每天 09:00 和 19:00 自动运行 `auto_sync.py`（仅工作日）
- 自动运行 pytest 测试，通过后 git push
- 结果通过钉钉机器人推送通知

```bash
# 手动触发（Headless 模式）
$env:PLAYWRIGHT_HEADLESS="1"; python auto_sync.py

# Dry-run（不执行推送）
python auto_sync.py --dry-run
```

### 方式二：GitHub Actions（云端运行，不依赖本地电脑）
- 定时触发：每天 UTC 1:00 = 北京时间 9:00（仅工作日）
- Push 到 main 分支自动触发
- 支持手动触发（workflow_dispatch）

**配置步骤：**
1. 在 GitHub 仓库 Settings → Secrets 添加：
   - `DINGTALK_TOKEN`: 钉钉机器人 access_token
   - `DINGTALK_SECRET`: 钉钉机器人密钥（SECxxx）
2. 在 Actions 页面启用 "Auto Test" workflow

**查看运行结果：**
- GitHub 仓库 → Actions → Auto Test
- 运行日志、测试报告、截图都在 artifacts 中

---

## 已知限制

- 全量测试（97 用例）约需 22 分钟，不适合高频 CI
- pytest-xdist 并行执行会导致 Playwright asyncio 冲突，不使用
- 如有 Chrome 进程残留导致超时：`taskkill /f /im chrome.exe`
- 定时任务需要 Headless 模式（`conftest.py` 自动检测）
