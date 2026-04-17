"""
回归测试管理模块
智能测试用例筛选、版本对比和自动化回归测试
"""

import os
import json
import yaml
import hashlib
import difflib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from datetime import datetime


@dataclass
class RegressionTestCase:
    """回归测试用例数据结构"""
    id: str
    description: str
    platform: str
    priority: str
    tags: List[str]
    last_run_time: datetime
    last_result: str
    execution_count: int
    success_rate: float
    change_impact: float  # 变更影响度


class RegressionManager:
    """回归测试管理器"""
    
    def __init__(self, config_path: str = "config/regression_config.yaml"):
        """初始化回归测试管理器"""
        self.config = self.load_config(config_path)
        self.test_cases = []
        self.version_history = []
        
    def load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {
                "regression": {
                    "strategy": "smart",
                    "threshold": 0.8,
                    "max_tests": 100,
                    "priority_weight": {
                        "high": 1.0,
                        "medium": 0.7,
                        "low": 0.3
                    }
                }
            }
    
    def load_test_cases(self, test_case_dir: str = "tests"):
        """加载测试用例"""
        if not os.path.exists(test_case_dir):
            return []
        
        test_cases = []
        
        # 遍历测试用例文件
        for filename in os.listdir(test_case_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(test_case_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        test_data = json.load(f)
                        
                        test_case = RegressionTestCase(
                            id=test_data.get("id", filename),
                            description=test_data.get("description", ""),
                            platform=test_data.get("platform", "web"),
                            priority=test_data.get("priority", "medium"),
                            tags=test_data.get("tags", []),
                            last_run_time=datetime.fromisoformat(test_data.get("last_run_time", datetime.now().isoformat())),
                            last_result=test_data.get("last_result", "unknown"),
                            execution_count=test_data.get("execution_count", 0),
                            success_rate=test_data.get("success_rate", 0.0),
                            change_impact=test_data.get("change_impact", 0.0)
                        )
                        
                        test_cases.append(test_case)
                except Exception as e:
                    print(f"加载测试用例失败 {filename}: {e}")
        
        self.test_cases = test_cases
        return test_cases
    
    def calculate_change_impact(self, version_diff: Dict, test_case: RegressionTestCase) -> float:
        """计算变更影响度"""
        impact_score = 0.0
        
        # 根据变更类型计算影响度
        if "ui_changes" in version_diff:
            ui_changes = version_diff["ui_changes"]
            if test_case.tags and "ui" in test_case.tags:
                impact_score += 0.4
        
        if "api_changes" in version_diff:
            api_changes = version_diff["api_changes"]
            if test_case.tags and "api" in test_case.tags:
                impact_score += 0.4
        
        if "function_changes" in version_diff:
            function_changes = version_diff["function_changes"]
            for tag in test_case.tags:
                if tag in function_changes:
                    impact_score += 0.3
        
        # 根据优先级调整权重
        priority_weight = self.config["regression"]["priority_weight"].get(test_case.priority, 0.7)
        impact_score *= priority_weight
        
        return impact_score
    
    def smart_selection(self, version_diff: Dict, max_tests: int = None) -> List[RegressionTestCase]:
        """智能测试用例筛选"""
        if max_tests is None:
            max_tests = self.config["regression"]["max_tests"]
        
        # 计算每个测试用例的变更影响度
        for test_case in self.test_cases:
            test_case.change_impact = self.calculate_change_impact(version_diff, test_case)
        
        # 按影响度排序
        sorted_tests = sorted(self.test_cases, key=lambda tc: tc.change_impact, reverse=True)
        
        # 筛选阈值以上的测试用例
        threshold = self.config["regression"]["threshold"]
        filtered_tests = [tc for tc in sorted_tests if tc.change_impact >= threshold]
        
        # 限制数量
        selected_tests = filtered_tests[:max_tests]
        
        return selected_tests
    
    def compare_versions(self, old_version: Dict, new_version: Dict) -> Dict:
        """版本对比"""
        diff = {
            "ui_changes": [],
            "api_changes": [],
            "function_changes": [],
            "performance_changes": []
        }
        
        # UI变更检测
        if old_version.get("ui") != new_version.get("ui"):
            diff["ui_changes"].append({
                "type": "ui",
                "old": old_version.get("ui"),
                "new": new_version.get("ui")
            })
        
        # API变更检测
        old_api = old_version.get("api", {})
        new_api = new_version.get("api", {})
        
        for api_name, api_data in new_api.items():
            if api_name not in old_api:
                diff["api_changes"].append({
                    "type": "added",
                    "api": api_name,
                    "data": api_data
                })
            elif api_data != old_api[api_name]:
                diff["api_changes"].append({
                    "type": "modified",
                    "api": api_name,
                    "old": old_api[api_name],
                    "new": api_data
                })
        
        for api_name, api_data in old_api.items():
            if api_name not in new_api:
                diff["api_changes"].append({
                    "type": "removed",
                    "api": api_name,
                    "data": api_data
                })
        
        # 功能变更检测
        old_features = old_version.get("features", {})
        new_features = new_version.get("features", {})
        
        for feature_name, feature_data in new_features.items():
            if feature_name not in old_features:
                diff["function_changes"].append({
                    "type": "added",
                    "feature": feature_name,
                    "data": feature_data
                })
            elif feature_data != old_features[feature_name]:
                diff["function_changes"].append({
                    "type": "modified",
                    "feature": feature_name,
                    "old": old_features[feature_name],
                    "new": feature_data
                })
        
        for feature_name, feature_data in old_features.items():
            if feature_name not in new_features:
                diff["function_changes"].append({
                    "type": "removed",
                    "feature": feature_name,
                    "data": feature_data
                })
        
        # 性能变更检测
        old_performance = old_version.get("performance", {})
        new_performance = new_version.get("performance", {})
        
        for metric_name, metric_value in new_performance.items():
            if metric_name in old_performance:
                old_value = old_performance[metric_name]
                if abs(metric_value - old_value) > old_value * 0.2:  # 20%变化
                    diff["performance_changes"].append({
                        "type": "significant",
                        "metric": metric_name,
                        "old": old_value,
                        "new": metric_value,
                        "change": metric_value - old_value
                    })
        
        return diff
    
    def analyze_failure(self, test_result: Dict) -> Dict:
        """分析失败原因"""
        analysis = {
            "failure_type": "",
            "root_cause": "",
            "suggested_fix": "",
            "impact_level": ""
        }
        
        # 分析错误信息
        errors = test_result.get("errors", [])
        
        if not errors:
            analysis["failure_type"] = "unknown"
            return analysis
        
        # 根据错误类型分类
        for error in errors:
            error_text = error
            
            if "element not found" in error_text.lower() or "selector" in error_text.lower():
                analysis["failure_type"] = "element_missing"
                analysis["root_cause"] = "UI元素变更或定位失效"
                analysis["suggested_fix"] = "更新元素定位器或检查UI变更"
                analysis["impact_level"] = "high"
            
            elif "api" in error_text.lower() or "http" in error_text.lower():
                analysis["failure_type"] = "api_change"
                analysis["root_cause"] = "API接口变更"
                analysis["suggested_fix"] = "更新API调用或检查接口文档"
                analysis["impact_level"] = "high"
            
            elif "login" in error_text.lower() or "authentication" in error_text.lower():
                analysis["failure_type"] = "auth_failure"
                analysis["root_cause"] = "认证机制变更"
                analysis["suggested_fix"] = "更新认证参数或检查权限设置"
                analysis["impact_level"] = "medium"
            
            elif "timeout" in error_text.lower() or "slow" in error_text.lower():
                analysis["failure_type"] = "performance_degradation"
                analysis["root_cause"] = "性能下降或网络问题"
                analysis["suggested_fix"] = "优化性能或检查网络连接"
                analysis["impact_level"] = "medium"
            
            else:
                analysis["failure_type"] = "generic_error"
                analysis["root_cause"] = "通用错误"
                analysis["suggested_fix"] = "检查测试环境和配置"
                analysis["impact_level"] = "low"
        
        return analysis
    
    def generate_regression_plan(self, version_diff: Dict) -> Dict:
        """生成回归测试计划"""
        # 智能筛选测试用例
        selected_tests = self.smart_selection(version_diff)
        
        # 分组测试用例
        test_groups = {
            "high_priority": [],
            "medium_priority": [],
            "low_priority": []
        }
        
        for test_case in selected_tests:
            if test_case.priority == "high":
                test_groups["high_priority"].append(test_case)
            elif test_case.priority == "medium":
                test_groups["medium_priority"].append(test_case)
            else:
                test_groups["low_priority"].append(test_case)
        
        # 生成计划
        plan = {
            "version_diff": version_diff,
            "total_tests": len(selected_tests),
            "high_priority_tests": len(test_groups["high_priority"]),
            "medium_priority_tests": len(test_groups["medium_priority"]),
            "low_priority_tests": len(test_groups["low_priority"]),
            "estimated_time": len(selected_tests) * 2,  # 假设每个测试2分钟
            "test_groups": test_groups,
            "recommended_order": [
                "high_priority",
                "medium_priority",
                "low_priority"
            ]
        }
        
        return plan
    
    def update_test_history(self, test_result: Dict):
        """更新测试历史"""
        test_id = test_result.get("test_id")
        
        # 找到对应的测试用例
        for test_case in self.test_cases:
            if test_case.id == test_id:
                test_case.last_run_time = datetime.now()
                test_case.last_result = test_result.get("status", "unknown")
                test_case.execution_count += 1
                
                # 更新成功率
                if test_case.last_result == "success":
                    test_case.success_rate = (test_case.success_rate * (test_case.execution_count - 1) + 1) / test_case.execution_count
                else:
                    test_case.success_rate = (test_case.success_rate * (test_case.execution_count - 1)) / test_case.execution_count
                
                break
    
    def save_test_case(self, test_case: RegressionTestCase):
        """保存测试用例"""
        test_data = {
            "id": test_case.id,
            "description": test_case.description,
            "platform": test_case.platform,
            "priority": test_case.priority,
            "tags": test_case.tags,
            "last_run_time": test_case.last_run_time.isoformat(),
            "last_result": test_case.last_result,
            "execution_count": test_case.execution_count,
            "success_rate": test_case.success_rate,
            "change_impact": test_case.change_impact
        }
        
        file_path = f"tests/{test_case.id}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
    
    def export_report(self, regression_results: List[Dict], filename: str = None) -> str:
        """导出回归测试报告"""
        if not filename:
            filename = f"regression_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_path = f"logs/{filename}"
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_tests": len(regression_results),
            "success_count": sum(1 for r in regression_results if r.get("status") == "success"),
            "failure_count": sum(1 for r in regression_results if r.get("status") == "failure"),
            "error_count": sum(1 for r in regression_results if r.get("status") == "error"),
            "total_duration": sum(r.get("duration", 0) for r in regression_results),
            "failure_analysis": [],
            "recommendations": []
        }
        
        # 分析失败用例
        for result in regression_results:
            if result.get("status") != "success":
                analysis = self.analyze_failure(result)
                report["failure_analysis"].append({
                    "test_id": result.get("test_id"),
                    "analysis": analysis
                })
        
        # 生成建议
        if report["failure_count"] > 0:
            report["recommendations"].append("检查UI变更并更新元素定位器")
            report["recommendations"].append("验证API接口变更")
            report["recommendations"].append("更新测试用例以适应系统变更")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_path


if __name__ == "__main__":
    # 示例使用
    manager = RegressionManager()
    
    # 加载测试用例
    manager.load_test_cases()
    
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
            "login": {"url": "/api/login", "method": "POST"},
            "user_info": {"url": "/api/user", "method": "GET"}
        },
        "features": {
            "login": {"enabled": True},
            "search": {"enabled": True}
        },
        "performance": {
            "load_time": 2.5,
            "response_time": 1.0
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
            "login": {"url": "/api/v2/login", "method": "POST"},
            "user_info": {"url": "/api/v2/user", "method": "GET"},
            "profile": {"url": "/api/v2/profile", "method": "GET"}  # 新增API
        },
        "features": {
            "login": {"enabled": True},
            "search": {"enabled": False},  # 功能变更
            "dashboard": {"enabled": True}  # 新增功能
        },
        "performance": {
            "load_time": 3.0,
            "response_time": 1.5
        }
    }
    
    # 版本对比
    version_diff = manager.compare_versions(old_version, new_version)
    
    print("版本变更:")
    print(json.dumps(version_diff, indent=2, ensure_ascii=False))
    
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