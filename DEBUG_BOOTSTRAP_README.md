# Debug Bootstrap 脚本使用指南

## 📝 脚本说明

这个调试脚本用于测试和调试 `opentelemetry-instrumentation` 包中的 `bootstrap.py` 的 `run()` 函数。

## 🚀 快速开始

### 1. 预览将要安装的插件（默认行为）

```bash
python debug_bootstrap.py
```

**输出示例**：
```
📦 将要安装的插件:

  1. opentelemetry-instrumentation-asyncio==0.61b0.dev
  2. opentelemetry-instrumentation-dbapi==0.61b0.dev
  3. opentelemetry-instrumentation-logging==0.61b0.dev
  4. opentelemetry-instrumentation-flask==0.61b0.dev
  5. opentelemetry-instrumentation-requests==0.61b0.dev
  ...

📊 总计: 12 个插件
```

---

### 2. 调试特定库的检测

```bash
# 检测 Flask
python debug_bootstrap.py --debug-library flask

# 检测 Django
python debug_bootstrap.py --debug-library django

# 检测 Requests
python debug_bootstrap.py --debug-library requests
```

**输出示例**：
```
🔍 检测库: flask

📦 库要求: flask >= 1.0
🔌 插件包: opentelemetry-instrumentation-flask==0.61b0.dev
✅ 已安装: True
```

---

### 3. 列出所有支持的库

```bash
python debug_bootstrap.py --list-all
```

**输出示例**：
```
📚 OpenTelemetry 支持的库（共 50+ 个）:

📂 Web 框架:
  ✅ flask >= 1.0
  ❌ django >= 1.10
  ✅ fastapi ~= 0.92
  ...

📂 HTTP 客户端:
  ✅ requests ~= 2.0
  ❌ httpx >= 0.18.0
  ...

📂 数据库:
  ✅ redis >= 2.6
  ❌ pymongo >= 3.1, < 5.0
  ...
```

---

### 4. 测试自定义库列表

```bash
python debug_bootstrap.py --test-custom
```

这个模式使用一个简化的测试库列表，不会实际安装任何包。

---

### 5. 实际运行 bootstrap（会调用 pip install）

```bash
# 仅列出需要安装的插件（不安装）
python debug_bootstrap.py --action requirements

# 实际安装插件（⚠️ 会执行 pip install）
python debug_bootstrap.py --action install
```

**⚠️ 警告**：`--action install` 会实际调用 `pip install` 安装插件！

---

## 📋 所有命令选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `--preview` | 预览将要安装的插件（默认） | `python debug_bootstrap.py --preview` |
| `--debug-library LIBRARY` | 调试特定库的检测逻辑 | `python debug_bootstrap.py --debug-library flask` |
| `--list-all` | 列出所有支持的库 | `python debug_bootstrap.py --list-all` |
| `--test-custom` | 测试自定义库列表 | `python debug_bootstrap.py --test-custom` |
| `--action requirements` | 列出需要安装的插件 | `python debug_bootstrap.py --action requirements` |
| `--action install` | 实际安装插件 | `python debug_bootstrap.py --action install` |

---

## 🎯 常见使用场景

### 场景 1：检查系统中哪些库会被检测到

```bash
# 方法 1：查看预览
python debug_bootstrap.py

# 方法 2：查看详细的检测信息
python debug_bootstrap.py --debug-library
```

---

### 场景 2：验证特定库的版本是否满足要求

```bash
# 检查 Flask 是否满足要求
python debug_bootstrap.py --debug-library flask

# 检查 Django 是否满足要求
python debug_bootstrap.py --debug-library django
```

**输出解读**：
- `✅ 已安装: True` → 库已安装且版本满足要求
- `✅ 已安装: False` → 库未安装或版本不满足要求

---

### 场景 3：了解 OpenTelemetry 支持哪些库

```bash
python debug_bootstrap.py --list-all
```

这会按类别列出所有支持的库，并标记哪些已安装。

---

### 场景 4：测试 run() 函数的逻辑（不实际安装）

```bash
# 测试自定义库列表
python debug_bootstrap.py --test-custom

# 或者查看完整的安装预览
python debug_bootstrap.py
```

---

### 场景 5：实际运行 bootstrap 安装插件

```bash
# 先预览
python debug_bootstrap.py --action requirements

# 确认无误后安装
python debug_bootstrap.py --action install
```

---

## 🔍 调试技巧

### 1. 查看详细日志

脚本已经配置了日志输出，如果需要更详细的日志：

```python
# 修改脚本中的日志级别
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

### 2. 测试特定的库列表

编辑脚本中的 `test_custom_libraries()` 函数：

```python
test_libraries = [
    {
        "library": "你的库 >= 版本",
        "instrumentation": "对应的插件包",
    },
    # 添加更多...
]
```

然后运行：
```bash
python debug_bootstrap.py --test-custom
```

---

### 3. 检查版本匹配逻辑

在 Python 交互式环境中：

```python
from opentelemetry.instrumentation.bootstrap import _is_installed

# 测试特定库
print(_is_installed("flask >= 1.0"))
print(_is_installed("django >= 1.10"))
print(_is_installed("requests ~= 2.0"))
```

---

## 📊 输出说明

### 符号含义

- ✅ - 已安装且版本满足要求
- ❌ - 未安装或版本不满足要求
- 📦 - 库/包
- 🔌 - 插件
- 🔍 - 检测/搜索
- 📋 - 列表
- 📂 - 类别
- 📊 - 统计
- ⚠️ - 警告
- 💡 - 提示

---

## ⚠️ 注意事项

1. **不要在生产环境直接使用 `--action install`**
   - 建议先使用 `--action requirements` 查看列表
   - 将输出保存到 `requirements.txt` 文件
   - 在测试环境验证后再部署

2. **版本冲突**
   - 脚本会在安装后执行 `pip check`
   - 如果有依赖冲突，会抛出异常

3. **Python 路径**
   - 脚本假设 `opentelemetry-instrumentation` 在当前目录下
   - 如果路径不同，需要修改脚本中的 `instrumentation_path`

---

## 🐛 故障排除

### 问题 1：ModuleNotFoundError

**错误**：
```
ModuleNotFoundError: No module named 'opentelemetry.instrumentation'
```

**解决**：
```bash
# 确保在正确的目录下运行
cd /Users/songji/Code/Python/opentelemetry-python-contrib

# 或者安装 opentelemetry-instrumentation
pip install opentelemetry-instrumentation
```

---

### 问题 2：权限错误

**错误**：
```
PermissionError: [Errno 13] Permission denied
```

**解决**：
```bash
# 使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 然后运行脚本
python debug_bootstrap.py
```

---

### 问题 3：版本检测不准确

**原因**：可能是 `bootstrap_gen.py` 过期

**解决**：
```bash
# 重新生成 bootstrap_gen.py
python scripts/generate_instrumentation_bootstrap.py
```

---

## 📚 相关文档

- [OpenTelemetry Python 文档](https://opentelemetry.io/docs/languages/python/)
- [自动插桩指南](https://opentelemetry.io/docs/languages/python/automatic/)
- [Bootstrap 源码](https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/opentelemetry-instrumentation/src/opentelemetry/instrumentation/bootstrap.py)

---

## 💡 扩展建议

### 1. 添加更多调试功能

```python
# 添加到脚本中
def check_version_compatibility(library, version):
    """检查特定版本是否兼容"""
    from packaging.requirements import Requirement
    req = Requirement(f"{library} {version}")
    # ... 实现检查逻辑
```

### 2. 生成安装报告

```python
def generate_report():
    """生成详细的安装报告"""
    # 保存到 JSON 或 HTML 文件
    pass
```

### 3. 集成到 CI/CD

```bash
# 在 CI 中使用
python debug_bootstrap.py --action requirements > otel-requirements.txt
pip install -r otel-requirements.txt
```

---

## 🎉 总结

这个调试脚本提供了多种方式来测试和理解 `bootstrap.py` 的 `run()` 函数：

1. ✅ **预览模式**：查看将要安装的插件
2. ✅ **调试模式**：检查特定库的检测逻辑
3. ✅ **列表模式**：查看所有支持的库
4. ✅ **测试模式**：使用自定义库列表测试
5. ✅ **执行模式**：实际运行 bootstrap 逻辑

**推荐工作流**：
```bash
# 1. 先预览
python debug_bootstrap.py

# 2. 检查特定库
python debug_bootstrap.py --debug-library flask

# 3. 查看所有支持的库
python debug_bootstrap.py --list-all

# 4. 确认后安装
python debug_bootstrap.py --action install
```

祝调试愉快！🚀
