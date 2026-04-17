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

# 运行全部测试（79 用例，约 17 分钟）
pytest tests/ -q

# 只跑某个模块
pytest tests/test_contract.py -q

# 只跑单个用例
pytest tests/test_contract.py::test_contract_stats_visible -v

# 跳过慢用例
pytest tests/ -q -m "not slow"
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
│   └── test_contract.py # 合同管理模块 14 用例
├── pages/               # Page Object 页面对象
│   ├── login_page.py
│   ├── workbench_page.py
│   └── contract_page.py
├── conftest.py          # pytest fixtures + 报告钩子
├── pytest.ini           # pytest 配置
├── generate_report.py   # 自定义报告生成器
├── requirements.txt     # 真实依赖（仅 5 个包）
├── logs/                # 截图和临时文件
└── reports/             # 测试报告输出目录
    ├── report.html      # 自定义中文 HTML 报告
    ├── report_data.json # 原始测试数据
    └── html-report.html # pytest-html 报告
```

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
2. **编写 Page Object** — `pages/xxx_page.py`，封装所有页面操作
3. **编写测试用例** — `tests/test_xxx.py`，使用 pytest fixtures
4. **注册 fixture** — 在 `conftest.py` 中添加 page object fixture
5. **运行验证** — `pytest tests/test_xxx.py -q`
6. **生成报告** — `python generate_report.py`

---

## 已知限制

- 全量测试（79 用例）约需 17 分钟，不适合高频 CI
- pytest-xdist 并行执行会导致 Playwright asyncio 冲突，不使用
- 如有 Chrome 进程残留导致超时：`taskkill /f /im chrome.exe`
