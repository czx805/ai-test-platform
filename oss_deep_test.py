#!/usr/bin/env python3
"""
深入分析OSS上传问题
测试是否因为SDK默认Content-Type导致绕过Policy限制
"""
import oss2
import json
import urllib.request
import os
import mimetypes

# 获取STS Token
def get_sts_token(path="wuyuan/task"):
    url = f"https://test6688.jh119.cn/bases/oss/jhy/sts/token?type=1&path={path}"
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer 245ea6c8-0456-4855-bd6a-b8f04cfa0064",
        "x-tenant-header": "wuyuan"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

def upload_with_explicit_content_type(token_data, local_file, oss_key, explicit_content_type):
    """使用明确的Content-Type上传"""
    sts = token_data['data']['stsToken']
    auth = oss2.StsStsAuth(sts['accessKeyId'], sts['accessKeySecret'], sts['securityToken'])
    bucket = oss2.Bucket(auth, "oss-cn-shanghai.aliyuncs.com", "fms-media")

    # 读取文件内容
    with open(local_file, 'rb') as f:
        content = f.read()

    try:
        result = bucket.put_object(oss_key, content, headers={'Content-Type': explicit_content_type})
        return result.status == 200, f"HTTP {result.status}"
    except oss2.exceptions.RequestError as e:
        return False, str(e)[:100]
    except Exception as e:
        return False, str(e)[:100]

def main():
    print("=" * 70)
    print("深入分析: 使用明确的Content-Type测试Policy限制")
    print("=" * 70)

    # 获取Token
    token_data = get_sts_token("wuyuan/task")
    sts = token_data['data']['stsToken']
    auth = oss2.StsAuth(sts['accessKeyId'], sts['accessKeySecret'], sts['securityToken'])
    bucket = oss2.Bucket(auth, "oss-cn-shanghai.aliyuncs.com", "fms-media")

    # Policy允许的类型
    policy_b64 = token_data['data']['policy']
    policy = json.loads(__import__('base64').b64decode(policy_b64).decode('utf-8'))
    allowed_types = policy['conditions'][2][2]

    print("\nPolicy允许的类型:")
    for t in allowed_types:
        print(f"  - {t}")

    print("\n" + "=" * 70)
    print("测试1: 使用text/plain上传txt文件")
    print("=" * 70)

    # 测试用text/plain上传txt
    txt_file = "D:/aitest/workbuddy/20260417101959/OSS不支持格式测试/test_doc.txt"
    oss_key = "yxf/wuyuan/task/test_policy/plain_txt_test.txt"

    with open(txt_file, 'rb') as f:
        content = f.read()

    try:
        result = bucket.put_object(oss_key, content, headers={'Content-Type': 'text/plain'})
        print(f"  text/plain + txt文件: HTTP {result.status} - {'意外通过' if result.status == 200 else '被拦截'}")
    except oss2.exceptions.RequestError as e:
        print(f"  text/plain + txt文件: 被拦截 - {str(e)[:60]}")
    except Exception as e:
        print(f"  错误: {e}")

    print("\n" + "=" * 70)
    print("测试2: 使用application/octet-stream上传exe文件")
    print("=" * 70)

    exe_file = "D:/aitest/workbuddy/20260417101959/OSS不支持格式测试/test_exe.exe"
    oss_key = "yxf/wuyuan/task/test_policy/octet_exe_test.exe"

    with open(exe_file, 'rb') as f:
        content = f.read()

    try:
        result = bucket.put_object(oss_key, content, headers={'Content-Type': 'application/octet-stream'})
        print(f"  octet-stream + exe文件: HTTP {result.status} - {'意外通过' if result.status == 200 else '被拦截'}")
    except oss2.exceptions.RequestError as e:
        print(f"  octet-stream + exe文件: 被拦截 - {str(e)[:60]}")
    except Exception as e:
        print(f"  错误: {e}")

    print("\n" + "=" * 70)
    print("测试3: 使用application/zip上传zip文件")
    print("=" * 70)

    zip_file = "D:/aitest/workbuddy/20260417101959/OSS不支持格式测试/test_archive.zip"
    oss_key = "yxf/wuyuan/task/test_policy/zip_test_upload.zip"

    with open(zip_file, 'rb') as f:
        content = f.read()

    try:
        result = bucket.put_object(oss_key, content, headers={'Content-Type': 'application/zip'})
        print(f"  application/zip + zip文件: HTTP {result.status} - {'意外通过' if result.status == 200 else '被拦截'}")
    except oss2.exceptions.RequestError as e:
        print(f"  application/zip + zip文件: 被拦截 - {str(e)[:60]}")
    except Exception as e:
        print(f"  错误: {e}")

    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)
    print("""
如果以上测试中:
- text/plain 被拦截 → Policy正确, 问题在SDK自动设置Content-Type
- text/plain 通过 → Policy未生效, 需要检查服务端配置

注意: OSS的Policy content-type条件是区分大小写的,
且必须是精确匹配才能生效。
    """)

if __name__ == "__main__":
    main()
