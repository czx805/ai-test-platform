"""
WEB测试引擎模块
支持浏览器自动化测试、视觉回归测试和API测试
"""

import yaml
import json
import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
import requests
from PIL import Image
import numpy as np


@dataclass
class TestResult:
    """测试结果数据结构"""
    test_id: str
    status: str  # success, failure, error
    duration: float
    screenshot_path: str
    logs: List[str]
    errors: List[str]
    performance_data: Dict[str, float]


class WebTestEngine:
    """WEB测试引擎"""
    
    def __init__(self, config_path: str = "config/web_config.yaml"):
        """初始化WEB测试引擎"""
        self.config = self.load_config(config_path)
        self.playwright = None
        self.browser = None
        self.page = None
        
    def load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {
                "web": {
                    "browsers": {
                        "chrome": {"enabled": True, "headless": False},
                        "firefox": {"enabled": True, "headless": False},
                        "edge": {"enabled": True, "headless": False}
                    },
                    "test_urls": {
                        "base_url": "http://localhost:8080"
                    }
                }
            }
    
    def setup_browser(self, browser_type: str = "chrome"):
        """设置浏览器"""
        browser_config = self.config["web"]["browsers"].get(browser_type)
        if not browser_config or not browser_config["enabled"]:
            raise ValueError(f"浏览器 {browser_type} 未启用")
        
        self.playwright = sync_playwright().start()
        
        if browser_type == "chrome":
            self.browser = self.playwright.chromium.launch(headless=browser_config["headless"])
        elif browser_type == "firefox":
            self.browser = self.playwright.firefox.launch(headless=browser_config["headless"])
        elif browser_type == "edge":
            self.browser = self.playwright.chromium.launch(headless=browser_config["headless"])
        else:
            raise ValueError(f"不支持浏览器类型: {browser_type}")
        
        self.page = self.browser.new_page()
        
        # 设置视口大小
        if "viewport" in self.config["web"]["browser_args"]:
            viewport = self.config["web"]["browser_args"]["viewport"]
            width, height = map(int, viewport.split('x'))
            self.page.set_viewport_size({"width": width, "height": height})
        
        return self.page
    
    def teardown_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def navigate_to(self, url: str):
        """导航到指定URL"""
        if not self.page:
            self.setup_browser()
        
        self.page.goto(url)
    
    def find_element(self, selector: str, timeout: int = 5000) -> Optional[Any]:
        """查找元素"""
        if not self.page:
            raise ValueError("页面未初始化")
        
        element = self.page.locator(selector)
        
        try:
            element.wait_for(state="visible", timeout=timeout)
            return element
        except:
            return None
    
    def click_element(self, selector: str):
        """点击元素"""
        element = self.find_element(selector)
        if element:
            element.click()
            return True
        return False
    
    def input_text(self, selector: str, text: str):
        """输入文本"""
        element = self.find_element(selector)
        if element:
            element.fill(text)
            return True
        return False
    
    def get_text(self, selector: str) -> Optional[str]:
        """获取文本"""
        element = self.find_element(selector)
        if element:
            return element.text_content()
        return None
    
    def screenshot(self, name: str = None):
        """截图"""
        if not name:
            name = f"screenshot_{int(time.time())}.png"
        
        screenshot_path = f"logs/{name}"
        self.page.screenshot(path=screenshot_path)
        return screenshot_path
    
    def visual_regression(self, screenshot_path: str, reference_path: str) -> float:
        """视觉回归测试"""
        # 读取图片
        screenshot_img = Image.open(screenshot_path)
        reference_img = Image.open(reference_path)
        
        # 转换为数组
        screenshot_arr = np.array(screenshot_img)
        reference_arr = np.array(reference_img)
        
        # 计算相似度
        similarity = self.calculate_similarity(screenshot_arr, reference_arr)
        
        return similarity
    
    def calculate_similarity(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """计算图片相似度"""
        if img1.shape != img2.shape:
            # 调整大小
            img2 = np.resize(img2, img1.shape)
        
        # 计算差异
        diff = np.abs(img1 - img2)
        
        # 计算相似度（0-1）
        similarity = 1 - (diff.sum() / (img1.shape[0] * img1.shape[1] * img1.shape[2] * 255))
        
        return similarity
    
    def api_test(self, url: str, method: str = "GET", data: Dict = None) -> Dict:
        """API测试"""
        try:
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json=data)
            elif method == "PUT":
                response = requests.put(url, json=data)
            elif method == "DELETE":
                response = requests.delete(url)
            else:
                raise ValueError(f"不支持的方法: {method}")
            
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json() if response.content else None,
                "time": response.elapsed.total_seconds(),
                "success": response.status_code < 400
            }
            
            return result
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
    
    def performance_test(self, url: str) -> Dict[str, float]:
        """性能测试"""
        if not self.page:
            self.setup_browser()
        
        # 导航到页面
        self.navigate_to(url)
        
        # 等待页面加载完成
        self.page.wait_for_load_state("networkidle")
        
        # 收集性能数据
        performance_data = {}
        
        # 获取加载时间
        performance_data["load_time"] = self.page.evaluate("performance.timing.loadEventEnd - performance.timing.navigationStart")
        
        # 获取DOM大小
        performance_data["dom_size"] = self.page.evaluate("document.querySelectorAll('*').length")
        
        # 获取内存使用
        performance_data["memory_usage"] = self.page.evaluate("performance.memory.usedJSHeapSize")
        
        # 获取请求数量
        performance_data["request_count"] = len(self.page.evaluate("performance.getEntriesByType('resource')"))
        
        return performance_data
    
    def run_test(self, test_case: Dict) -> TestResult:
        """运行测试用例"""
        test_id = test_case.get("id", f"test_{int(time.time())}")
        
        # 初始化结果
        result = TestResult(
            test_id=test_id,
            status="success",
            duration=0,
            screenshot_path="",
            logs=[],
            errors=[],
            performance_data={}
        )
        
        start_time = time.time()
        
        try:
            # 设置浏览器
            browser_type = test_case.get("browser", "chrome")
            self.setup_browser(browser_type)
            
            # 记录日志
            result.logs.append(f"启动 {browser_type} 浏览器")
            
            # 执行测试步骤
            for step in test_case.get("steps", []):
                action = step.get("action")
                selector = step.get("selector")
                data = step.get("data")
                
                result.logs.append(f"执行步骤: {action}")
                
                if action == "navigate":
                    self.navigate_to(data)
                elif action == "click":
                    success = self.click_element(selector)
                    if not success:
                        result.errors.append(f"点击失败: {selector}")
                        result.status = "failure"
                elif action == "input":
                    success = self.input_text(selector, data)
                    if not success:
                        result.errors.append(f"输入失败: {selector}")
                        result.status = "failure"
                elif action == "verify":
                    text = self.get_text(selector)
                    expected_text = step.get("expected_text")
                    if text != expected_text:
                        result.errors.append(f"验证失败: 期望 '{expected_text}', 实际 '{text}'")
                        result.status = "failure"
                elif action == "screenshot":
                    screenshot_path = self.screenshot()
                    result.screenshot_path = screenshot_path
                    result.logs.append(f"截图保存到: {screenshot_path}")
                
                # 等待短暂时间
                time.sleep(0.5)
            
            # 性能测试
            if test_case.get("performance_test"):
                url = test_case.get("url")
                performance_data = self.performance_test(url)
                result.performance_data = performance_data
            
            # API测试
            if test_case.get("api_test"):
                api_url = test_case.get("api_url")
                api_method = test_case.get("api_method", "GET")
                api_data = test_case.get("api_data")
                api_result = self.api_test(api_url, api_method, api_data)
                result.logs.append(f"API测试结果: {api_result}")
                if not api_result.get("success"):
                    result.errors.append(f"API测试失败: {api_result}")
                    result.status = "failure"
            
            # 视觉回归测试
            if test_case.get("visual_regression"):
                screenshot_path = self.screenshot()
                reference_path = test_case.get("reference_path")
                similarity = self.visual_regression(screenshot_path, reference_path)
                result.logs.append(f"视觉相似度: {similarity}")
                if similarity < test_case.get("threshold", 0.95):
                    result.errors.append(f"视觉回归失败: 相似度 {similarity}")
                    result.status = "failure"
            
            # 计算持续时间
            result.duration = time.time() - start_time
            
        except Exception as e:
            result.status = "error"
            result.errors.append(f"测试执行异常: {str(e)}")
        
        finally:
            # 关闭浏览器
            self.teardown_browser()
        
        return result
    
    def generate_report(self, results: List[TestResult]) -> Dict:
        """生成测试报告"""
        report = {
            "total_tests": len(results),
            "success_count": sum(1 for r in results if r.status == "success"),
            "failure_count": sum(1 for r in results if r.status == "failure"),
            "error_count": sum(1 for r in results if r.status == "error"),
            "total_duration": sum(r.duration for r in results),
            "average_duration": sum(r.duration for r in results) / len(results),
            "details": []
        }
        
        for result in results:
            report["details"].append({
                "test_id": result.test_id,
                "status": result.status,
                "duration": result.duration,
                "screenshot": result.screenshot_path,
                "logs": result.logs,
                "errors": result.errors,
                "performance": result.performance_data
            })
        
        return report
    
    def save_report(self, report: Dict, filename: str = None):
        """保存测试报告"""
        if not filename:
            filename = f"test_report_{int(time.time())}.json"
        
        report_path = f"logs/{filename}"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_path


if __name__ == "__main__":
    # 示例使用
    engine = WebTestEngine()
    
    # 示例测试用例
    test_case = {
        "id": "web_login_test",
        "description": "网站登录测试",
        "browser": "chrome",
        "steps": [
            {"action": "navigate", "data": "http://localhost:8080/login"},
            {"action": "input", "selector": "input[name='username']", "data": "testuser"},
            {"action": "input", "selector": "input[name='password']", "data": "testpass"},
            {"action": "click", "selector": "button[type='submit']"},
            {"action": "verify", "selector": ".success-message", "expected_text": "登录成功"}
        ],
        "api_test": True,
        "api_url": "http://localhost:8080/api/login",
        "api_method": "POST",
        "api_data": {"username": "testuser", "password": "testpass"},
        "visual_regression": True,
        "reference_path": "reference/login_page.png",
        "threshold": 0.95
    }
    
    # 运行测试
    result = engine.run_test(test_case)
    
    print("测试结果:")
    print(f"状态: {result.status}")
    print(f"持续时间: {result.duration}")
    print(f"日志: {result.logs}")
    print(f"错误: {result.errors}")
    
    # 生成报告
    report = engine.generate_report([result])
    report_path = engine.save_report(report)
    print(f"报告保存到: {report_path}")