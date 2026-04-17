# AI测试平台快速开始指南

## 1. 环境准备

### 安装Python
确保已安装Python 3.8或更高版本。

### 安装依赖
```bash
pip install -r requirements.txt
```

### 安装Playwright浏览器
```bash
python -m playwright install
```

## 2. 配置平台

### 配置文件
编辑以下配置文件：

1. **config/ai_config.yaml** - AI配置
   - OpenAI API密钥
   - Claude API密钥
   - 生成参数

2. **config/web_config.yaml** - WEB测试配置
   - 浏览器配置
   - 测试URL
   - 元素定位策略

3. **config/miniprogram_config.yaml** - 小程序配置
   - 微信开发者工具路径
   - 小程序AppID
   - 测试参数

4. **config/regression_config.yaml** - 回归测试配置
   - 回归策略
   - 筛选阈值
   - 优先级权重

## 3. 快速示例

### 生成测试用例
```bash
python main.py --action generate --description "测试网站登录功能：首先打开登录页面，然后输入用户名和密码，最后点击登录按钮，应该看到登录成功提示"
```

### 运行WEB测试
```bash
python main.py --action run --platform web --test-case tests/web_login_test.json
```

### 运行小程序测试
```bash
python main.py --action run --platform miniprogram --test-case tests/miniprogram_search_test.json
```

### 回归测试分析
```bash
python main.py --action regression
```

### 失败分析
```bash
python main.py --action analyze
```

## 4. 核心功能

### AI测试用例生成器
- 自然语言描述转换为测试代码
- 智能元素定位与路径生成
- 跨平台代码适配（WEB/小程序）

### WEB测试引擎
- 多浏览器兼容性测试（Chrome、Firefox、Edge）
- DOM操作与事件测试
- 视觉回归测试
- API接口测试
- 性能测试

### 小程序测试引擎
- 微信小程序模拟环境
- 小程序API功能测试
- 跨平台兼容性测试（iOS/Android）
- 微信授权和支付功能测试

### 回归测试管理器
- 智能测试用例筛选
- 版本对比与变更检测
- 自动化回归测试执行
- 失败用例智能分析

## 5. 高级用法

### 集成CI/CD
```bash
# Jenkins Pipeline示例
stage('AI测试') {
    steps {
        sh 'python main.py --action regression'
    }
}
```

### 自定义测试用例
```json
{
    "id": "custom_test",
    "description": "自定义测试用例",
    "platform": "web",
    "priority": "high",
    "tags": ["custom", "ui"],
    "steps": [
        {
            "action": "navigate",
            "data": "http://your-site.com"
        },
        {
            "action": "click",
            "selector": ".your-element"
        }
    ]
}
```

### 扩展功能
1. **添加新的测试类型**：修改 src/ 目录下的模块
2. **自定义AI模型**：修改 config/ai_config.yaml
3. **添加新的浏览器**：修改 config/web_config.yaml
4. **自定义回归策略**：修改 config/regression_config.yaml

## 6. 常见问题

### Q: AI生成代码不准确怎么办？
A: 调整AI配置中的temperature参数，或提供更详细的测试用例描述

### Q: 浏览器无法启动怎么办？
A: 检查Playwright是否正确安装，或修改headless模式为False

### Q: 小程序测试失败怎么办？
A: 检查微信开发者工具配置，确保路径正确且小程序已打开

### Q: 回归测试筛选不准确怎么办？
A: 调整config/regression_config.yaml中的threshold参数

## 7. 性能优化

### 并行执行
```bash
python main.py --action run --platform web --test-case tests/web_login_test.json --parallel true
```

### 缓存优化
- 启用浏览器缓存
- 复用测试会话
- 智能等待策略

### 资源管理
- 限制并发测试数量
- 监控内存使用
- 自动清理资源