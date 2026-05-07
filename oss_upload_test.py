#!/usr/bin/env python3
"""
OSS上传验证测试脚本
测试Policy对不同文件类型的限制是否生效
"""
import oss2
import json
import urllib.request
import os
import time
import mimetypes

# 测试文件路径
ALLOWED_DIR = "D:/aitest/workbuddy/20260417101959/OSS测试文件"
NOT_ALLOWED_DIR = "D:/aitest/workbuddy/20260417101959/OSS不支持格式测试"

# 获取STS Token
def get_sts_token(path="wuyuan/task"):
    url = f"https://test6688.jh119.cn/bases/oss/jhy/sts/token?type=1&path={path}"
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer 245ea6c8-0456-4855-bd6a-b8f04cfa0064",
        "x-tenant-header": "wuyuan"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

def test_upload(token_data, local_file, oss_key):
    """测试上传单个文件"""
    sts = token_data['data']['stsToken']
    auth = oss2.StsAuth(sts['accessKeyId'], sts['accessKeySecret'], sts['securityToken'])
    bucket = oss2.Bucket(auth, "oss-cn-shanghai.aliyuncs.com", "fms-media")

    # 获取文件的Content-Type
    content_type, _ = mimetypes.guess_type(local_file)
    if not content_type:
        content_type = 'application/octet-stream'

    try:
        result = bucket.put_object_from_file(oss_key, local_file, progress_callback=None)
        if result.status == 200:
            return True, f"上传成功 (HTTP 200)"
        else:
            return False, f"上传失败 (HTTP {result.status})"
    except oss2.exceptions.RequestError as e:
        return False, f"OSS错误: {e}"
    except Exception as e:
        return False, f"错误: {str(e)[:80]}"

def main():
    print("=" * 70)
    print("OSS上传验证测试")
    print("=" * 70)

    # 获取Token
    print("\n[1] 获取STS Token...")
    token_data = get_sts_token("wuyuan/task")
    print(f"    AccessKeyId: {token_data['data']['stsToken']['accessKeyId'][:30]}...")

    # Policy允许的类型
    policy_b64 = token_data['data']['policy']
    policy = json.loads(__import__('base64').b64decode(policy_b64).decode('utf-8'))
    allowed_types = policy['conditions'][2][2]
    print(f"    Policy允许类型数: {len(allowed_types)}")

    print("\n" + "=" * 70)
    print("测试清单内格式 (应该成功)")
    print("=" * 70)

    # 测试允许的文件类型
    allowed_tests = [
        ("test_image.png", "yxf/wuyuan/task/test_policy/png_test.png"),
        ("test_image.jpg", "yxf/wuyuan/task/test_policy/jpg_test.jpg"),
        ("test_image.svg", "yxf/wuyuan/task/test_policy/svg_test.svg"),
        ("test_pdf.pdf", "yxf/wuyuan/task/test_policy/pdf_test.pdf"),
        ("test_data.csv", "yxf/wuyuan/task/test_policy/csv_test.csv"),
    ]

    success_count = 0
    fail_count = 0
    for filename, oss_key in allowed_tests:
        local_path = os.path.join(ALLOWED_DIR, filename)
        if os.path.exists(local_path):
            success, msg = test_upload(token_data, local_path, oss_key)
            status = "✅" if success else "❌"
            print(f"  {status} {filename}: {msg}")
            if success:
                success_count += 1
            else:
                fail_count += 1
        else:
            print(f"  ⚠️ {filename}: 文件不存在")

    print("\n" + "=" * 70)
    print("测试清单外格式 (应该失败)")
    print("=" * 70)

    # 测试不允许的文件类型
    not_allowed_tests = [
        ("test_doc.txt", "yxf/wuyuan/task/test_policy/txt_test.txt"),
        ("test_archive.zip", "yxf/wuyuan/task/test_policy/zip_test.zip"),
        ("test_exe.exe", "yxf/wuyuan/task/test_policy/exe_test.exe"),
        ("test_doc.rtf", "yxf/wuyuan/task/test_policy/rtf_test.rtf"),
        ("test_doc.html", "yxf/wuyuan/task/test_not_allowed/html_test.html"),
    ]

    # 确保html文件存在
    html_path = os.path.join(NOT_ALLOWED_DIR, "test_doc.html")
    if not os.path.exists(html_path):
        with open(html_path, 'w') as f:
            f.write("<html><body>test</body></html>")

    blocked_count = 0
    passed_count = 0
    for filename, oss_key in not_allowed_tests:
        local_path = os.path.join(NOT_ALLOWED_DIR, filename)
        if os.path.exists(local_path):
            success, msg = test_upload(token_data, local_path, oss_key)
            if not success:
                print(f"  ✅ {filename}: 正确拦截 - {msg}")
                blocked_count += 1
            else:
                print(f"  ❌ {filename}: 意外通过! {msg}")
                passed_count += 1
        else:
            print(f"  ⚠️ {filename}: 文件不存在")

    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    print(f"  清单内格式测试: {success_count} 成功, {fail_count} 失败")
    print(f"  清单外格式测试: {blocked_count} 正确拦截, {passed_count} 意外通过")

    if fail_count == 0 and passed_count == 0:
        print("\n🎉 所有测试通过! Policy配置正确生效")
    else:
        print("\n⚠️ 发现问题, 请检查上述失败的测试项")

if __name__ == "__main__":
    main()
