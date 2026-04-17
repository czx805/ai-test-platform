"""
AI测试用例生成器模块
基于自然语言描述生成测试代码
"""

import yaml
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TestCase:
    """测试用例数据结构"""
    id: str
    description: str
    platform: str  # web, miniprogram
    steps: List[Dict]
    expected_results: List[str]
    priority: str  # high, medium, low
    tags: List[str]


class AIGenerator:
    """AI测试用例生成器"""
    
    def __init__(self, config_path: str = "config/ai_config.yaml"):
        """初始化AI生成器"""
        self.config = self.load_config(config_path)
        self.platform_mappings = {
            "web": self.generate_web_code,
            "miniprogram": self.generate_miniprogram_code
        }
        
    def load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {
                "ai": {
                    "openai": {"api_key": "", "model": "gpt-4"},
                    "anthropic": {"api_key": "", "model": "claude-3-sonnet"},
                    "local": {"enabled": False, "model_path": ""}
                }
            }
    
    def parse_natural_language(self, description: str) -> TestCase:
        """解析自然语言描述，提取测试用例信息"""
        # 提取平台信息
        platform = self.extract_platform(description)
        
        # 提取测试步骤
        steps = self.extract_steps(description)
        
        # 提取预期结果
        expected_results = self.extract_expected_results(description)
        
        # 生成用例ID
        case_id = f"test_{platform}_{self.generate_hash(description)}"
        
        # 提取标签
        tags = self.extract_tags(description)
        
        return TestCase(
            id=case_id,
            description=description,
            platform=platform,
            steps=steps,
            expected_results=expected_results,
            priority="medium",
            tags=tags
        )
    
    def extract_platform(self, description: str) -> str:
        """从描述中提取平台信息"""
        if "小程序" in description or "微信" in description:
            return "miniprogram"
        elif "网页" in description or "网站" in description or "浏览器" in description:
            return "web"
        else:
            return "web"  # 默认WEB平台
    
    def extract_steps(self, description: str) -> List[Dict]:
        """从描述中提取测试步骤"""
        steps = []
        
        # 使用正则表达式提取步骤
        step_patterns = [
            r"首先(.+)",
            r"然后(.+)",
            r"接着(.+)",
            r"最后(.+)",
            r"输入(.+)",
            r"点击(.+)",
            r"选择(.+)",
            r"打开(.+)",
            r"登录(.+)",
            r"搜索(.+)"
        ]
        
        for pattern in step_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                step_type = self.determine_step_type(match)
                steps.append({
                    "action": match.strip(),
                    "type": step_type,
                    "target": self.extract_target(match),
                    "data": self.extract_data(match)
                })
        
        # 如果没有提取到步骤，使用简单分割
        if not steps:
            sentences = re.split(r'[。；，]', description)
            for sentence in sentences:
                if sentence.strip():
                    step_type = self.determine_step_type(sentence)
                    steps.append({
                        "action": sentence.strip(),
                        "type": step_type,
                        "target": self.extract_target(sentence),
                        "data": self.extract_data(sentence)
                    })
        
        return steps
    
    def determine_step_type(self, step_text: str) -> str:
        """确定步骤类型"""
        if "点击" in step_text or "选择" in step_text:
            return "click"
        elif "输入" in step_text or "填写" in step_text:
            return "input"
        elif "打开" in step_text or "访问" in step_text:
            return "open"
        elif "登录" in step_text or "登入" in step_text:
            return "login"
        elif "搜索" in step_text or "查找" in step_text:
            return "search"
        elif "验证" in step_text or "检查" in step_text:
            return "verify"
        else:
            return "generic"
    
    def extract_target(self, step_text: str) -> Optional[str]:
        """提取操作目标"""
        # 提取按钮、链接、输入框等目标
        target_patterns = [
            r"点击(.+)按钮",
            r"选择(.+)选项",
            r"输入(.+)框",
            r"打开(.+)页面",
            r"访问(.+)网站"
        ]
        
        for pattern in target_patterns:
            match = re.search(pattern, step_text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_data(self, step_text: str) -> Optional[str]:
        """提取操作数据"""
        # 提取输入的数据内容
        data_patterns = [
            r"输入(.+)",
            r"填写(.+)",
            r"搜索(.+)",
            r"输入(.+)到(.+)"
        ]
        
        for pattern in data_patterns:
            match = re.search(pattern, step_text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_expected_results(self, description: str) -> List[str]:
        """提取预期结果"""
        results = []
        
        # 提取预期结果
        result_patterns = [
            r"应该(.+)",
            r"预期(.+)",
            r"结果(.+)",
            r"看到(.+)",
            r"显示(.+)",
            r"出现(.+)"
        ]
        
        for pattern in result_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                results.append(match.strip())
        
        return results
    
    def extract_tags(self, description: str) -> List[str]:
        """提取测试标签"""
        tags = []
        
        # 根据关键词提取标签
        keyword_tags = {
            "登录": "login",
            "注册": "register",
            "搜索": "search",
            "支付": "payment",
            "表单": "form",
            "列表": "list",
            "详情": "detail",
            "导航": "navigation"
        }
        
        for keyword, tag in keyword_tags.items():
            if keyword in description:
                tags.append(tag)
        
        return tags
    
    def generate_hash(self, text: str) -> str:
        """生成简单的哈希值"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()[:8]
    
    def generate_gherkin(self, test_case: TestCase) -> str:
        """生成Gherkin格式的测试用例"""
        gherkin_lines = []
        
        # Feature描述
        gherkin_lines.append(f"Feature: {test_case.description}")
        gherkin_lines.append("")
        
        # Scenario标题
        gherkin_lines.append(f"  Scenario: {test_case.description}")
        gherkin_lines.append("")
        
        # Given条件
        gherkin_lines.append(f"    Given 我打开了{test_case.platform}应用")
        gherkin_lines.append("")
        
        # When步骤
        for step in test_case.steps:
            action_text = step["action"]
            gherkin_lines.append(f"    When {action_text}")
        gherkin_lines.append("")
        
        # Then预期结果
        for result in test_case.expected_results:
            gherkin_lines.append(f"    Then {result}")
        
        return "\n".join(gherkin_lines)
    
    def generate_web_code(self, gherkin_text: str) -> str:
        """生成WEB测试代码"""
        # 解析Gherkin
        scenario = self.parse_gherkin(gherkin_text)
        
        # 生成Python测试代码
        code = f"""
from behave import given, when, then
from playwright.sync_api import sync_playwright

@given('我打开了web应用')
def step_open_web(context):
    context.playwright = sync_playwright().start()
    context.browser = context.playwright.chromium.launch(headless=False)
    context.page = context.browser.new_page()
    context.page.goto("{scenario['base_url']}")

"""
        
        for step in scenario["steps"]:
            if step.get("type","") == "click":
                code += f"""
@when('{step["action"]}')
def step_click(context):
    element = context.page.locator('button:text("{step["target"]}")')
    element.click()
"""
            elif step.get("type","") == "input":
                code += f"""
@when('{step["action"]}')
def step_input(context):
    element = context.page.locator('input[placeholder="{step["target"]}"]')
    element.fill("{step["data"]}")
"""
            elif step.get("type","") == "open":
                code += f"""
@when('{step["action"]}')
def step_open(context):
    context.page.goto("{step["data"]}")
"""
        
        for result in scenario["expected_results"]:
            code += f"""
@then('{result}')
def step_verify(context):
    # 验证预期结果
    assert context.page.locator('text("{result}")').is_visible()
"""
        
        code += """
def after_scenario(context):
    context.browser.close()
    context.playwright.stop()
"""
        
        return code
    
    def generate_miniprogram_code(self, gherkin_text: str) -> str:
        """生成小程序测试代码"""
        # 解析Gherkin
        scenario = self.parse_gherkin(gherkin_text)
        
        # 生成Python测试代码
        code = f"""
from behave import given, when, then
from miniprogram_automation import MiniProgramDriver

@given('我打开了miniprogram应用')
def step_open_miniprogram(context):
    context.driver = MiniProgramDriver(appid="{scenario['appid']}")
    context.driver.launch()

"""
        
        for step in scenario["steps"]:
            if step.get("type","") == "click":
                code += f"""
@when('{step["action"]}')
def step_click(context):
    element = context.driver.find_element_by_text("{step["target"]}")
    element.click()
"""
            elif step.get("type","") == "input":
                code += f"""
@when('{step["action"]}')
def step_input(context):
    element = context.driver.find_element_by_placeholder("{step["target"]}")
    element.send_keys("{step["data"]}")
"""
            elif step.get("type","") == "open":
                code += f"""
@when('{step["action"]}')
def step_open(context):
    context.driver.navigate_to("{step["data"]}")
"""
        
        for result in scenario["expected_results"]:
            code += f"""
@then('{result}')
def step_verify(context):
    # 验证预期结果
    assert context.driver.find_element_by_text("{result}").is_visible()
"""
        
        code += """
def after_scenario(context):
    context.driver.close()
"""
        
        return code
    
    def parse_gherkin(self, gherkin_text: str) -> Dict:
        """解析Gherkin文本"""
        lines = gherkin_text.split('\n')
        scenario = {
            "description": "",
            "base_url": "http://localhost:8080",
            "appid": "your_appid",
            "steps": [],
            "expected_results": []
        }
        
        for line in lines:
            if line.startswith("Feature:"):
                scenario["description"] = line.replace("Feature:", "").strip()
            elif line.startswith("    When"):
                action = line.replace("    When", "").strip()
                scenario["steps"].append({"action": action})
            elif line.startswith("    Then"):
                result = line.replace("    Then", "").strip()
                scenario["expected_results"].append(result)
        
        return scenario
    
    def generate_test_code(self, description: str) -> Tuple[str, str]:
        """生成测试代码"""
        # 解析自然语言
        test_case = self.parse_natural_language(description)
        
        # 生成Gherkin
        gherkin = self.generate_gherkin(test_case)
        
        # 生成Python代码
        if test_case.platform == "web":
            code = self.generate_web_code(gherkin)
        else:
            code = self.generate_miniprogram_code(gherkin)
        
        return gherkin, code


if __name__ == "__main__":
    # 示例使用
    generator = AIGenerator()
    
    # WEB测试示例
    web_description = "测试网站登录功能：首先打开登录页面，然后输入用户名和密码，最后点击登录按钮，应该看到登录成功提示"
    web_gherkin, web_code = generator.generate_test_code(web_description)
    
    print("WEB测试Gherkin:")
    print(web_gherkin)
    print("\nWEB测试代码:")
    print(web_code)
    
    # 小程序测试示例
    mp_description = "测试小程序搜索功能：首先打开小程序首页，然后点击搜索框，输入关键词搜索，应该看到搜索结果列表"
    mp_gherkin, mp_code = generator.generate_test_code(mp_description)
    
    print("\n小程序测试Gherkin:")
    print(mp_gherkin)
    print("\n小程序测试代码:")
    print(mp_code)