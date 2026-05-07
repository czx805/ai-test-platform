#!/usr/bin/env python3
"""
直接HTTP请求测试OSS Policy - 使用urllib
"""
import oss2
import json
import base64
import hashlib
import hmac
import time
import urllib.request
import urllib.parse

def get_sts_token():
    """获取STS Token"""
    url = "https://test6688.jh119.cn/bases/oss/jhy/sts/token?type=1&path=wuyuan/task"
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer 245ea6c8-0456-4855-bd6a-b8f04cfa0064",
        "x-tenant-header": "wuyuan"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

def upload_with_signature(sts_data, content, content_type, test_name):
    """使用OSS签名方式上传"""
    sts = sts_data['data']['stsToken']
    oss_key = f"yxf/wuyuan/task/test_policy/{test_name}"

    # 构造URL
    encoded_key = urllib.parse.quote(oss_key)
    url = f"https://fms-media.oss-cn-shanghai.aliyuncs.com/{encoded_key}"

    # 生成日期
    date_gmt = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())

    # 构造签名串
    signed_str = f"PUT\n\n{content_type}\n{date_gmt}\n/{oss_key.replace('/', '%2F')}"

    # 计算签名
    signature = base64.b64encode(
        hmac.new(
            sts['accessKeySecret'].encode('utf-8'),
            signed_str.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('utf-8')

    # 构造Authorization头
    auth = f"OSS {sts['accessKeyId']}:{signature}"

    # 构造请求
    req = urllib.request.Request(
        url,
        data=content,
        method='PUT'
    )
    req.add_header('Content-Type', content_type)
    req.add_header('Date', date_gmt)
    req.add_header('Authorization', auth)
    req.add_header('x-oss-security-token', sts['securityToken'])

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return e.code, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return 0, f"错误: {e.reason}"

def main():
    print("=" * 70)
    print("Policy限制测试结果汇总")
    print("=" * 70)

    # 获取Token
    print("\n[1] 获取STS Token...")
    sts_data = get_sts_token()

    # 显示Policy
    policy_b64 = sts_data['data']['policy']
    policy = json.loads(base64.b64decode(policy_b64).decode('utf-8'))
    allowed = policy['conditions'][2][2]
    print(f"    Policy允许 {len(allowed)} 种Content-Type")

    print("\n" + "=" * 70)
    print("[2] Policy限制测试")
    print("=" * 70)

    # 测试案例
    tests = [
        # 清单内格式
        ("image/png", b"fake png", "test_allowed_png.png"),
        ("text/csv", "col1,col2\n1,2", "test_allowed_csv.csv"),
        ("application/pdf", b"%PDF-1.4 fake", "test_allowed_pdf.pdf"),

        # 清单外格式
        ("text/plain", "hello text", "test_blocked_txt.txt"),
        ("application/octet-stream", b"binary", "test_blocked_bin.bin"),
        ("application/zip", b"PK fake zip", "test_blocked_zip.zip"),
        ("text/html", "<html></html>", "test_blocked_html.html"),
        ("application/javascript", "alert(1)", "test_blocked_js.js"),
    ]

    results = []
    for content_type, content, name in tests:
        if isinstance(content, str):
            content = content.encode('utf-8')

        status, msg = upload_with_signature(sts_data, content, content_type, name)

        # 判断是否应该被允许
        is_allowed = content_type in allowed
        is_blocked = status != 200

        if is_allowed:
            expected = "应成功"
            actual = "成功" if status == 200 else f"失败({status})"
            result = "✅" if status == 200 else "❌"
        else:
            expected = "应拦截"
            actual = "拦截" if is_blocked else "意外通过"
            result = "✅" if is_blocked else "❌"

        print(f"  {result} [{content_type}]")
        print(f"      期望: {expected}, 实际: {actual}")
        print()

        results.append({
            'type': content_type,
            'allowed': is_allowed,
            'blocked': is_blocked,
            'ok': (is_allowed and not is_blocked) or (not is_allowed and is_blocked)
        })

    # 汇总
    print("=" * 70)
    print("[3] 测试结果汇总")
    print("=" * 70)

    ok_count = sum(1 for r in results if r['ok'])
    total_count = len(results)

    print(f"\n  通过: {ok_count}/{total_count}")

    if ok_count == total_count:
        print("\n🎉 所有测试通过! Policy配置正确")
    else:
        failed = [r for r in results if not r['ok']]
        print(f"\n⚠️ 发现 {len(failed)} 个问题:")
        for r in failed:
            issue = "清单内格式被拦截" if r['allowed'] else "清单外格式意外通过"
            print(f"    - {r['type']}: {issue}")

        print("\n" + "=" * 70)
        print("[4] 问题分析")
        print("=" * 70)
        print("""
可能原因:
1. Policy的content-type条件格式不正确
   - 当前格式: ["in", "$content-type", [...]]
   - 正确格式: [["in", "$content-type", [...]]]

2. OSS Bucket未启用强制Policy验证
   - 需要在OSS控制台检查Bucket Policy设置

3. Policy签名验证未启用
   - 检查Bucket的"授权策略"是否强制验证

建议措施:
- 联系后端开发检查Policy生成逻辑
- 检查OSS Bucket的Policy配置
- 确认x-oss-security-token是否正确传递
        """)

if __name__ == "__main__":
    main()
