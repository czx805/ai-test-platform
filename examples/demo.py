"""
AI测试平台示例演示
"""

import sys
sys.path.append('src')

from ai_generator import AIGenerator
from web_test_engine import WebTestEngine
from miniprogram_test_engine import MiniProgramTestEngine
from regression_manager import RegressionManager


def demo_ai_generator():
    """演示AI测试用例生成器"""
    print("=== AI测试用例生成器演示 ===")
    
    generator = AIGenerator()
    
    # WEB测试示例
    web_description = "测试网站登录功能：首先打开登录页面，然后输入用户名和密码，最后点击登录按钮，应该看到登录成功提示"
    web_gherkin, web_code = generator.generate_test_code(web_description)
    
    print("WEB测试用例描述:", web_description)
    print("生成的Gherkin:")
    print(web_gherkin)
    print("生成的Python代码:")
    print(web_code[:200])  # 只显示前200字符
    
    # 小程序测试示例
    mp_description = "测试小程序搜索功能：首先打开小程序首页，然后点击搜索框，输入关键词搜索，应该看到搜索结果列表"
    mp_gherkin, mp_code = generator.generate_test_code(mp_description)
    
    print("\n小程序测试用例描述:", mp_description)
    print("生成的Gherkin:")
    print(mp_gherkin)
    print("生成的Python代码:")
    print(mp_code[:200])  # 只显示前200字符


def demo_web_test_engine():
    """演示WEB测试引擎"""
    print("\n=== WEB测试引擎演示 ===")
    
    engine = WebTestEngine()
    
    # 创建测试用例
    test_case = {
        "id": "demo_web_test",
        "description": "演示WEB测试",
        "browser": "chrome",
        "steps": [
            {"action": "navigate", "data": "https://example.com"},
            {"action": "screenshot", "selector": None, "data": None}
        ]
    }
    
    print("测试用例:", test_case)
    
    # 运行测试（模拟）
    print("注意：由于没有实际的浏览器环境，这里只是演示API调用")
    print("实际使用时需要配置浏览器和URL")


def demo_miniprogram_test_engine():
    """演示小程序测试引擎"""
    print("\n=== 小程序测试引擎演示 ===")
    
    engine = MiniProgramTestEngine()
    
    # 创建测试用例
    test_case = {
        "id": "demo_miniprogram_test",
        "description": "演示小程序测试",
        "steps": [
            {"action": "navigate", "data": "pages/home/home"},
            {"action": "click", "selector": ".search-button", "data": None}
        ],
        "wechat_api_test": True,
        "api_name": "user.login",
        "api_params": {"username": "testuser", "password": "testpass"}
    }
    
    print("测试用例:", test_case)
    
    # 运行测试（模拟）
    print("注意：由于没有实际的微信开发者工具环境，这里只是演示API调用")
    print("实际使用时需要配置微信开发者工具路径和小程序AppID")


def demo_regression_manager():
    """演示回归测试管理器"""
    print("\n=== 回归测试管理器演示 ===")
    
    manager = RegressionManager()
    
    # 版本对比示例
    old_version = {
        "ui": {
            "login_page": {
                "username_input": "input[name='username']",
                "password_input": "input[name='password']",
                "login_button": "button[type='submit']"
            }
        },
        "api": {
            "login": {"url": "/api/login", "method": "POST"}
        },
        "features": {
            "login": {"enabled": True}
        }
    }
    
    new_version = {
        "ui": {
            "login_page": {
                "username_input": "input[data-test='username']",
                "password_input": "input[data-test='password']",
                "login_button": "button[data-test='submit']"
            }
        },
        "api": {
            "login": {"url": "/api/v2/login", "method": "POST"}
        },
        "features": {
            "login": {"enabled": True}
        }
    }
    
    # 版本对比
    version_diff = manager.compare_versions(old_version, new_version)
    
    print("版本对比结果:")
    print("UI变更:", version_diff.get("ui_changes", []))
    print("API变更:", version_diff.get("api_changes", []))
    print("功能变更:", version_diff.get("function_changes", []))
    
    # 智能筛选测试用例
    selected_tests = manager.smart_selection(version_diff)
    
    print(f"\n智能筛选结果: {len(selected_tests)} 个测试用例")
    
    # 生成回归测试计划
    regression_plan = manager.generate_regression_plan(version_diff)
    
    print("\n回归测试计划:")
    print(f"总计测试用例: {regression_plan['total_tests']}")
    print(f"高优先级测试: {regression_plan['high_priority_tests']}")
    print(f"中优先级测试: {regression_plan['medium_priority_tests']}")
    print(f"低优先级测试: {regression_plan['low_priority_tests']}")
    print(f"预计时间: {regression_plan['estimated_time']} 分钟")


def main():
    """主函数"""
    print("AI测试平台示例演示")
    print("==================")
    
    # 演示各模块功能
    demo_ai_generator()
    demo_web_test_engine()
    demo_miniprogram_test_engine()
    demo_regression_manager()
    
    print("\n=== 使用说明 ===")
    print("1. 运行 setup.py 配置环境")
    print("2. 编辑 config/ai_config.yaml 配置AI参数")
    print("3. 运行 python main.py --action generate --description '测试用例描述'")
    print("4. 运行 python main.py --action run --platform web --test-case tests/web_login_test.json")
    print("5. 运行 python main.py --action regression 进行回归测试")


if __name__ == "__main__":
    main()