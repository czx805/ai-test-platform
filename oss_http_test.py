#!/usr/bin/env python3
"""
直接使用HTTP请求测试OSS Policy限制
绕过SDK,直接发送带Content-Type的请求
"""
import requests
import json
import base64
import hashlib
import hmac
import time
import os

def get_sts_token():
    """获取STS Token"""
    url = "https://test6688.jh119.cn/bases/oss/jhy/sts/token?type=1&path=wuyuan/task"
    resp = requests.get(url, headers={
        "Authorization": "Bearer 245ea6c8-0456-4855-bd6a-b8f04cfa0064",
        "x-tenant-header": "wuyuan"
    })
    return resp.json()

def upload_via_oss(sts_data, file_content, content_type, test_name):
    """直接通过OSS HTTP API上传"""
    sts = sts_data['data']['stsToken']

    # 生成oss_key
    oss_key = f"yxf/wuyuan/task/test_policy/{test_name}"

    # 构造上传URL
    endpoint = f"https://fms-media.oss-cn-shanghai.aliyuncs.com/{oss_key}"

    # 生成签名时间
    date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())

    # 构造签名串
    signed_string = f"PUT\n\n{content_type}\n{date}\n/{oss_key.replace('/', '%2F')}"

    # 计算签名 (使用AccessKeySecret)
    signature = base64.b64encode(
        hmac.new(
            sts['accessKeySecret'].encode('utf-8'),
            signed_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('utf-8')

    # 构造认证header
    auth_header = f"OSS {sts['accessKeyId']}:{signature}"

    # 发送PUT请求
    headers = {
        'Content-Type': content_type,
        'Date': date,
        'Authorization': auth_header,
        'x-oss-security-token': sts['securityToken']
    }

    try:
        resp = requests.put(endpoint, data=file_content, headers=headers, timeout=30)
        return resp.status_code, resp.text[:200] if resp.text else "No response body"
    except requests.exceptions.RequestException as e:
        return 0, str(e)

def main():
    print("=" * 70)
    print("直接HTTP请求测试OSS Policy限制")
    print("=" * 70)

    # 获取Token
    print("\n获取STS Token...")
    sts_data = get_sts_token()
    print(f"  AccessKeyId: {sts_data['data']['stsToken']['accessKeyId'][:30]}...")

    # 显示Policy内容
    policy_b64 = sts_data['data']['policy']
    policy = json.loads(base64.b64decode(policy_b64).decode('utf-8'))
    print(f"\nPolicy过期时间: {policy['expiration']}")
    allowed_types = policy['conditions'][2][2]
    print(f"允许的Content-Type: {len(allowed_types)}种")

    print("\n" + "=" * 70)
    print("测试: 清单内格式 (应该成功)")
    print("=" * 70)

    # 测试允许的类型
    allowed_tests = [
        ("text/plain", "hello world", "allowed_txt.txt"),
        ("image/png", b"\x89PNG\r\n\x1a\n" + b"fake png content", "allowed_png.png"),
    ]

    for content_type, content, name in allowed_tests:
        status, msg = upload_via_oss(sts_data, content, content_type, name)
        result = "✅ 成功" if status == 200 else f"❌ 失败({status})"
        print(f"  {result} - {content_type}: {msg[:50]}")

    print("\n" + "=" * 70)
    print("测试: 清单外格式 (应该被拦截)")
    print("=" * 70)

    # 测试不允许的类型
    not_allowed_tests = [
        ("text/plain", "dangerous content", "blocked_txt.txt"),
        ("application/octet-stream", b"binary data", "blocked_octet.bin"),
        ("application/zip", b"PK fake zip", "blocked_zip.zip"),
        ("application/javascript", "console.log('xss')", "blocked_js.js"),
        ("text/html", "<script>alert(1)</script>", "blocked_html.html"),
    ]

    blocked_count = 0
    passed_count = 0

    for content_type, content, name in not_allowed_tests:
        status, msg = upload_via_oss(sts_data, content, content_type, name)
        if status != 200:
            print(f"  ✅ 被拦截 - {content_type}: HTTP {status}")
            blocked_count += 1
        else:
            print(f"  ❌ 意外通过 - {content_type}")
            passed_count += 1

    print("\n" + "=" * 70)
    print("结果汇总")
    print("=" * 70)
    print(f"  拦截成功: {blocked_count}")
    print(f"  意外通过: {passed_count}")

    if passed_count == 0:
        print("\n🎉 Policy限制生效,所有不允许的类型都被拦截!")
    else:
        print(f"\n⚠️ Policy未生效, {passed_count}个不允许的类型意外通过!")
        print("\n可能原因:")
        print("  1. Policy的content-type条件格式不正确")
        print("  2. Bucket未启用Policy强制执行")
        print("  3. Policy签名验证未启用")

if __name__ == "__main__":
    main()
