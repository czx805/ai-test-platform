"""
generate_report.py
读取 reports/report_data.json，生成美化的中文 HTML 报告。
直接双击运行，或命令行: python generate_report.py
"""
import json, os, sys
from datetime import datetime

# ── 配置 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH  = os.path.join(SCRIPT_DIR, "reports", "report_data.json")
OUT_PATH   = os.path.join(SCRIPT_DIR, "reports", "report.html")


def load_data():
    if not os.path.exists(JSON_PATH):
        print(f"[ERROR] 未找到报告数据: {JSON_PATH}")
        print(f"请先运行 pytest 生成 JSON 数据")
        sys.exit(1)
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def status_badge(outcome):
    icons = {
        "passed":  ("✓", "通过", "#1a7f4b"),
        "failed":  ("✗", "失败", "#d93636"),
        "skipped": ("◌", "跳过", "#8c8c8c"),
    }
    ico, label, color = icons.get(outcome, ("?", outcome, "#999"))
    return f"""<span class="badge" style="background:{color}">
        <span class="badge-icon">{ico}</span>
        <span class="badge-label">{label}</span>
    </span>"""


def module_section(module_name, tests):
    rows = ""
    for t in tests:
        outcome = t["outcome"]
        duration = f'{t["duration"]:.3f}s'
        failure = t.get("failure_msg", "")
        screenshot = t.get("screenshot", "")

        # 失败时显示原因
        fail_block = ""
        if outcome == "failed" and failure:
            fail_block = f'<div class="failure-msg">❌ {failure}</div>'

        # 截图
        shot_block = ""
        if screenshot and os.path.exists(screenshot):
            shot_block = f'<div class="screenshot-wrap"><img src="file:///{os.path.abspath(screenshot)}" alt="截图" loading="lazy" onclick="this.classList.toggle(\'zoom\')" /></div>'

        # 时间颜色
        dur_color = "#1a7f4b" if outcome == "passed" else "#d93636"

        rows += f"""
        <tr class="row-{outcome}">
            <td class="col-status">{status_badge(outcome)}</td>
            <td class="col-title">
                <div class="test-name">{t['title']}</div>
                {fail_block}
                {shot_block}
            </td>
            <td class="col-dur" style="color:{dur_color}">{duration}</td>
        </tr>"""

    # 按 module 着色
    colors = {
        "login":    "#1976d2",
        "workbench": "#7b1fa2",
        "contract": "#e65100",
    }
    accent = colors.get(module_name, "#555")

    # 成功率
    total_m  = len(tests)
    passed_m = sum(1 for t in tests if t["outcome"] == "passed")
    rate_m   = f"{round(passed_m/total_m*100, 1)}%" if total_m else "0%"

    return f"""
<div class="module-block" data-module="{module_name}">
    <div class="module-header" style="border-left: 4px solid {accent}">
        <span class="module-name">{module_name}</span>
        <span class="module-meta">
            <span class="tag" style="background:{accent}">{total_m} 个用例</span>
            <span class="tag tag-pass">✓ {passed_m}</span>
            <span class="tag tag-fail">✗ {total_m - passed_m}</span>
            <span class="module-rate">通过率 {rate_m}</span>
        </span>
    </div>
    <table class="test-table">
        <thead>
            <tr>
                <th class="col-status">状态</th>
                <th class="col-title">测试用例</th>
                <th class="col-dur">耗时</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</div>"""


def render(data):
    # ── Summary cards ───────────────────────────────────────
    total   = data["total"]
    passed  = data["passed"]
    failed  = data["failed"]
    skipped = data["skipped"]
    rate    = data["pass_rate"]
    dur     = data["duration_s"]
    gen_at  = data["generated_at"]

    # 饼图 SVG
    if total:
        pct_pass = passed / total * 100
        pct_fail = failed / total * 100
        pct_skip = skipped / total * 100
        # 环形进度
        R = 50; C = 2 * 3.14159 * R
        dash_pass = C * pct_pass / 100
        dash_fail = C * pct_fail / 100
        dash_skip = C * pct_skip / 100
        # offset: pass 从顶部开始，fail 接在 pass 后，skip 接在 fail 后
        offset_fail = C - dash_pass
        offset_skip = C - dash_pass - dash_fail
        pie_svg = f"""
        <svg class="pie" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
          <circle r="{R}" cx="60" cy="60" fill="none" stroke="#e8e8e8" stroke-width="16"/>
          <circle r="{R}" cx="60" cy="60" fill="none" stroke="#d93636" stroke-width="16"
            stroke-dasharray="{dash_fail} {C}"
            stroke-dashoffset="{offset_fail}"
            stroke-linecap="butt" style="transition:stroke-dasharray .3s"/>
          <circle r="{R}" cx="60" cy="60" fill="none" stroke="#8c8c8c" stroke-width="16"
            stroke-dasharray="{dash_skip} {C}"
            stroke-dashoffset="{offset_skip}"
            stroke-linecap="butt" style="transition:stroke-dasharray .3s"/>
          <circle r="{R}" cx="60" cy="60" fill="none" stroke="#1a7f4b" stroke-width="16"
            stroke-dasharray="{dash_pass} {C}"
            stroke-dashoffset="0"
            stroke-linecap="butt" style="transition:stroke-dasharray .3s"/>
          <text x="60" y="54" text-anchor="middle" font-size="18" font-weight="700" fill="#222">{passed}</text>
          <text x="60" y="70" text-anchor="middle" font-size="11" fill="#888">通过</text>
        </svg>"""
    else:
        pie_svg = ""

    summary_cards = f"""
    <div class="summary-cards">
        <div class="card card-total">
            <div class="card-num">{total}</div>
            <div class="card-label">总用例</div>
        </div>
        <div class="card card-pass">
            <div class="card-num">{passed}</div>
            <div class="card-label">通过</div>
        </div>
        <div class="card card-fail">
            <div class="card-num">{failed}</div>
            <div class="card-label">失败</div>
        </div>
        <div class="card card-skip">
            <div class="card-num">{skipped}</div>
            <div class="card-label">跳过</div>
        </div>
        <div class="card card-rate">
            <div class="card-num" style="color:{'#1a7f4b' if failed==0 else '#d93636'}">{rate}</div>
            <div class="card-label">通过率</div>
        </div>
        <div class="card card-dur">
            <div class="card-num">{dur:.0f}s</div>
            <div class="card-label">总耗时</div>
        </div>
    </div>
    <div class="chart-area">
        {pie_svg}
    </div>"""

    # ── Group by module ────────────────────────────────────
    by_module = {}
    for t in data.get("tests", []):
        mod = t.get("module", "unknown")
        by_module.setdefault(mod, []).append(t)

    modules_html = "\n".join(
        module_section(mod, tests)
        for mod, tests in sorted(by_module.items())
    )

    # ── Overall status banner ───────────────────────────────
    if failed == 0:
        banner = '<div class="banner banner-pass">✅ 全部通过</div>'
    else:
        banner = f'<div class="banner banner-fail">❌ {failed} 个用例失败</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>测试报告 · {gen_at}</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
    --bg:       #f0f2f5;
    --surface:  #ffffff;
    --border:   #e0e0e0;
    --text:     #1a1a2e;
    --text-dim: #6b7280;
    --pass:     #1a7f4b;
    --fail:     #d93636;
    --skip:     #8c8c8c;
    --radius:   12px;
}}

body {{
    font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 14px;
    line-height: 1.6;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 16px 48px;
}}

/* ── Header ──────────────────────────────────── */
.report-header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #2d3a5a 100%);
    color: #fff;
    padding: 32px;
    border-radius: var(--radius);
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}}
.report-header::before {{
    content: "";
    position: absolute;
    top: -40px; right: -40px;
    width: 200px; height: 200px;
    background: rgba(255,255,255,.04);
    border-radius: 50%;
}}
.report-header h1 {{
    font-size: 22px; font-weight: 700;
    margin-bottom: 4px;
}}
.report-header .gen-time {{
    font-size: 12px; color: rgba(255,255,255,.5);
}}

/* ── Summary ──────────────────────────────────── */
.summary-wrap {{
    display: flex;
    gap: 20px;
    align-items: center;
    margin-bottom: 32px;
    flex-wrap: wrap;
}}
.summary-cards {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    flex: 1;
}}
.card {{
    background: var(--surface);
    border-radius: var(--radius);
    padding: 16px 20px;
    min-width: 80px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    text-align: center;
}}
.card-num {{
    font-size: 28px; font-weight: 800;
    line-height: 1.2;
}}
.card-total .card-num {{ color: var(--text); }}
.card-pass  .card-num {{ color: var(--pass); }}
.card-fail  .card-num {{ color: var(--fail); }}
.card-skip  .card-num {{ color: var(--skip); }}
.card-label {{ font-size: 11px; color: var(--text-dim); margin-top: 2px; text-transform: uppercase; letter-spacing: .5px; }}
.chart-area {{
    flex-shrink: 0;
}}
.pie {{ width: 110px; height: 110px; }}

/* ── Banner ───────────────────────────────────── */
.banner {{
    padding: 12px 20px;
    border-radius: var(--radius);
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 24px;
}}
.banner-pass {{ background: #d4edda; color: var(--pass); }}
.banner-fail {{ background: #f8d7da; color: var(--fail); }}

/* ── Module blocks ────────────────────────────── */
.module-block {{
    background: var(--surface);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
}}
.module-header {{
    padding: 14px 20px;
    background: #fafafa;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}}
.module-name {{
    font-size: 15px; font-weight: 700; color: var(--text);
}}
.module-meta {{
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
    margin-left: auto;
}}
.tag {{
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px; font-weight: 600; color: #fff;
}}
.tag-pass {{ background: #d4edda; color: var(--pass); }}
.tag-fail {{ background: #f8d7da; color: var(--fail); }}
.module-rate {{ font-size: 12px; color: var(--text-dim); }}

/* ── Test table ───────────────────────────────── */
.test-table {{
    width: 100%;
    border-collapse: collapse;
}}
.test-table thead tr {{
    background: #fafafa;
}}
.test-table th {{
    padding: 10px 16px;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: .5px;
    border-bottom: 1px solid var(--border);
}}
.col-status {{ width: 80px; }}
.col-dur    {{ width: 80px; text-align: right !important; }}
.col-title  {{ }}
.test-table td {{
    padding: 10px 16px;
    border-bottom: 1px solid #f0f0f0;
    vertical-align: top;
}}
.test-table tr:last-child td {{ border-bottom: none; }}
.row-failed td {{ background: #fff8f8; }}
.row-skipped td {{ background: #fafafa; color: var(--skip); }}

/* ── Badge ────────────────────────────────────── */
.badge {{
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 12px; font-weight: 600; color: #fff;
}}
.badge-icon {{ font-size: 11px; }}

/* ── Test name ────────────────────────────────── */
.test-name {{
    font-size: 13px; font-weight: 500; color: var(--text);
}}

/* ── Failure message ─────────────────────────── */
.failure-msg {{
    margin-top: 6px;
    padding: 6px 10px;
    background: #fff0f0;
    border-left: 3px solid var(--fail);
    border-radius: 0 4px 4px 0;
    font-size: 12px;
    color: var(--fail);
    word-break: break-all;
    max-width: 700px;
}}

/* ── Screenshot ───────────────────────────────── */
.screenshot-wrap {{
    margin-top: 8px;
}}
.screenshot-wrap img {{
    max-width: 400px;
    max-height: 250px;
    border-radius: 6px;
    border: 1px solid var(--border);
    cursor: zoom-in;
    transition: box-shadow .2s;
}}
.screenshot-wrap img:hover {{
    box-shadow: 0 4px 20px rgba(0,0,0,.15);
}}
.screenshot-wrap img.zoom {{
    max-width: 90vw; max-height: 80vh;
}}

/* ── Footer ───────────────────────────────────── */
.report-footer {{
    text-align: center;
    color: var(--text-dim);
    font-size: 12px;
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
}}

/* ── Duration ─────────────────────────────────── */
.col-dur {{
    font-family: "SF Mono", "Cascadia Code", monospace;
    font-size: 12px;
    white-space: nowrap;
    text-align: right;
}}

/* ── Responsive ───────────────────────────────── */
@media (max-width: 600px) {{
    .summary-wrap {{ flex-direction: column; align-items: stretch; }}
    .summary-cards {{ justify-content: center; }}
    .col-dur {{ display: none; }}
    .test-table th.col-dur {{ display: none; }}
    .screenshot-wrap img {{ max-width: 100%; }}
}}
</style>
</head>
<body>
<div class="container">

    <!-- Header -->
    <div class="report-header">
        <h1>📋 AI Test Platform · 自动化测试报告</h1>
        <div class="gen-time">生成时间：{gen_at} &nbsp;|&nbsp; 平台：{data.get("platform","Windows (Playwright)")}</div>
    </div>

    <!-- Summary -->
    {summary_cards}

    <!-- Overall banner -->
    {banner}

    <!-- Module sections -->
    {modules_html}

    <div class="report-footer">
        由 AI Test Platform 自动化测试框架生成 &nbsp;|&nbsp; pytest + Playwright
    </div>
</div>
</body>
</html>"""


def main():
    data = load_data()
    html = render(data)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Report: {OUT_PATH}")
    print(f"     Total={data['total']} Passed={data['passed']} Failed={data['failed']} Skipped={data['skipped']}")


if __name__ == "__main__":
    main()
