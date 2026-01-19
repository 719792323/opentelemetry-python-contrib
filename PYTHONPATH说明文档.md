# PYTHONPATH 详细说明文档

## 📖 目录

- [什么是 PYTHONPATH](#什么是-pythonpath)
- [核心概念](#核心概念)
- [使用场景](#使用场景)
- [设置方法](#设置方法)
- [实际示例](#实际示例)
- [注意事项](#注意事项)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 什么是 PYTHONPATH

**PYTHONPATH** 是一个**环境变量**，用于告诉 Python 解释器在导入模块时应该搜索哪些额外的目录。

### 简单理解

当你在 Python 中执行 `import some_module` 时，Python 需要知道去哪里找这个模块。PYTHONPATH 就是告诉 Python："嘿，除了默认的地方，你还可以去这些目录找找看！"

---

## 核心概念

### 1. Python 模块搜索机制

Python 导入模块时的搜索顺序：

```
1️⃣ 当前脚本所在目录
2️⃣ PYTHONPATH 环境变量指定的目录（如果设置了）
3️⃣ Python 标准库目录
4️⃣ site-packages 目录（第三方包安装位置）
```

### 2. 查看当前搜索路径

```python
import sys
print(sys.path)
```

**输出示例**：
```python
[
    '/Users/songji/Code/Python/my_project',              # 当前目录
    '/Users/songji/.local/lib/python3.9/site-packages',  # 用户包
    '/usr/lib/python3.9',                                 # 标准库
    '/usr/lib/python3.9/site-packages',                   # 系统包
]
```

### 3. PYTHONPATH 的作用

- ✅ 添加**自定义目录**到模块搜索路径
- ✅ 允许导入**未安装**的包
- ✅ 支持**多个目录**（用分隔符连接）
- ✅ 优先级**高于** site-packages

---

## 使用场景

### 场景 1：开发中的包（未安装）

**项目结构**：
```
my_project/
├── app.py
└── mylib/
    ├── __init__.py
    └── utils.py
```

**问题**：在其他目录运行 `app.py` 时找不到 `mylib`

**解决方案**：
```bash
export PYTHONPATH=/path/to/my_project
python /path/to/my_project/app.py  # ✅ 现在可以找到 mylib
```

---

### 场景 2：共享工具库

**目录结构**：
```
/opt/shared_libs/
├── common_utils/
│   ├── __init__.py
│   └── helpers.py
└── data_processing/
    ├── __init__.py
    └── processors.py
```

**设置**：
```bash
export PYTHONPATH=/opt/shared_libs
```

**使用**：
```python
# 在任何项目中都可以导入
from common_utils import helpers
from data_processing import processors
```

---

### 场景 3：OpenTelemetry 开发

在 OpenTelemetry 项目中测试未安装的包：

```bash
# 添加 opentelemetry-instrumentation 源码目录
export PYTHONPATH=/Users/songji/Code/Python/opentelemetry-python-contrib/opentelemetry-instrumentation/src

# 现在可以导入未安装的模块
python -c "from opentelemetry.instrumentation.auto_instrumentation import run"
```

---

### 场景 4：临时覆盖已安装的包

**用途**：测试修改后的代码，而不影响已安装的版本

```bash
# 假设已安装 mypackage 1.0，但想测试开发版本 2.0
export PYTHONPATH=/path/to/mypackage-dev
python test_script.py  # 使用开发版本
```

---

## 设置方法

### 方法 1：临时设置（当前终端会话）

#### macOS / Linux

```bash
# 单个路径
export PYTHONPATH=/path/to/modules

# 多个路径（用冒号分隔）
export PYTHONPATH=/path1:/path2:/path3

# 追加到现有 PYTHONPATH
export PYTHONPATH=/new/path:$PYTHONPATH
```

#### Windows (CMD)

```cmd
# 单个路径
set PYTHONPATH=C:\path\to\modules

# 多个路径（用分号分隔）
set PYTHONPATH=C:\path1;C:\path2;C:\path3
```

#### Windows (PowerShell)

```powershell
# 单个路径
$env:PYTHONPATH="C:\path\to\modules"

# 多个路径
$env:PYTHONPATH="C:\path1;C:\path2;C:\path3"
```

---

### 方法 2：永久设置

#### macOS / Linux

编辑 shell 配置文件：

**Bash** (`~/.bashrc` 或 `~/.bash_profile`)：
```bash
export PYTHONPATH=/path/to/modules:$PYTHONPATH
```

**Zsh** (`~/.zshrc`)：
```bash
export PYTHONPATH=/path/to/modules:$PYTHONPATH
```

**应用更改**：
```bash
source ~/.zshrc  # 或 ~/.bashrc
```

#### Windows

**系统环境变量**：
1. 右键"此电脑" → 属性
2. 高级系统设置 → 环境变量
3. 在"系统变量"或"用户变量"中：
   - 新建变量名：`PYTHONPATH`
   - 变量值：`C:\path1;C:\path2`

---

### 方法 3：在 Python 脚本中动态设置

```python
import sys
import os

# 方式 1：使用 sys.path.insert（推荐）
sys.path.insert(0, '/path/to/modules')

# 方式 2：使用 sys.path.append
sys.path.append('/path/to/modules')

# 方式 3：修改环境变量（需要在导入前）
os.environ['PYTHONPATH'] = '/path/to/modules'

# 现在可以导入该路径下的模块
import my_module
```

**区别**：
- `insert(0, path)`：添加到**最前面**（最高优先级）
- `append(path)`：添加到**最后面**（最低优先级）

---

### 方法 4：命令行一次性设置

```bash
# macOS / Linux
PYTHONPATH=/path/to/modules python script.py

# 多个路径
PYTHONPATH=/path1:/path2:/path3 python script.py

# Windows (CMD)
set PYTHONPATH=C:\path\to\modules && python script.py

# Windows (PowerShell)
$env:PYTHONPATH="C:\path\to\modules"; python script.py
```

---

## 实际示例

### 示例 1：OpenTelemetry 开发环境

```bash
# 设置多个 OpenTelemetry 包的源码路径
export PYTHONPATH=\
/Users/songji/Code/Python/opentelemetry-python-contrib/opentelemetry-instrumentation/src:\
/Users/songji/Code/Python/opentelemetry-python-contrib/opentelemetry-distro/src:\
/Users/songji/Code/Python/opentelemetry-python-contrib/instrumentation/opentelemetry-instrumentation-flask/src

# 验证导入
python -c "
from opentelemetry.instrumentation.auto_instrumentation import run
from opentelemetry.distro import OpenTelemetryDistro
from opentelemetry.instrumentation.flask import FlaskInstrumentor
print('✅ All imports successful!')
"
```

---

### 示例 2：调试脚本

创建 `debug_pythonpath.py`：

```python
#!/usr/bin/env python3
"""调试 PYTHONPATH 和模块搜索路径"""

import sys
import os

def print_separator(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

# 1. 显示 PYTHONPATH 环境变量
print_separator("PYTHONPATH 环境变量")
pythonpath = os.environ.get('PYTHONPATH', '(未设置)')
if pythonpath != '(未设置)':
    paths = pythonpath.split(os.pathsep)
    for i, path in enumerate(paths, 1):
        print(f"  {i}. {path}")
else:
    print(f"  {pythonpath}")

# 2. 显示 sys.path 内容
print_separator("sys.path 模块搜索路径")
for i, path in enumerate(sys.path, 1):
    # 标记路径来源
    if path == '':
        source = "(当前目录)"
    elif 'site-packages' in path:
        source = "(第三方包)"
    elif 'lib/python' in path:
        source = "(标准库)"
    else:
        source = ""
    
    print(f"  {i:2d}. {path} {source}")

# 3. 测试模块导入
print_separator("测试模块导入")

test_modules = [
    'opentelemetry.instrumentation.auto_instrumentation',
    'opentelemetry.distro',
    'opentelemetry.sdk.environment_variables',
]

for module_name in test_modules:
    try:
        module = __import__(module_name, fromlist=[''])
        location = getattr(module, '__file__', '(内置模块)')
        print(f"  ✅ {module_name}")
        print(f"     位置: {location}")
    except ImportError as e:
        print(f"  ❌ {module_name}")
        print(f"     错误: {e}")

print("\n" + "=" * 80 + "\n")
```

**使用**：

```bash
# 不设置 PYTHONPATH
python debug_pythonpath.py

# 设置 PYTHONPATH
PYTHONPATH=/Users/songji/Code/Python/opentelemetry-python-contrib/opentelemetry-instrumentation/src \
python debug_pythonpath.py
```

---

### 示例 3：项目启动脚本

创建 `run_with_pythonpath.sh`：

```bash
#!/bin/bash
# OpenTelemetry 开发环境启动脚本

# 设置项目根目录
PROJECT_ROOT="/Users/songji/Code/Python/opentelemetry-python-contrib"

# 设置 PYTHONPATH
export PYTHONPATH="\
${PROJECT_ROOT}/opentelemetry-instrumentation/src:\
${PROJECT_ROOT}/opentelemetry-distro/src:\
${PROJECT_ROOT}/instrumentation/opentelemetry-instrumentation-flask/src:\
${PROJECT_ROOT}/instrumentation/opentelemetry-instrumentation-requests/src"

# 显示设置的路径
echo "已设置 PYTHONPATH:"
echo "$PYTHONPATH" | tr ':' '\n' | nl

# 运行 Python 脚本
echo -e "\n运行脚本: $@"
python "$@"
```

**使用**：

```bash
chmod +x run_with_pythonpath.sh
./run_with_pythonpath.sh my_script.py
```

---

## 注意事项

### ⚠️ 1. 路径分隔符

不同操作系统使用不同的分隔符：

| 操作系统 | 分隔符 | 示例 |
|---------|-------|------|
| macOS / Linux | `:` (冒号) | `/path1:/path2:/path3` |
| Windows | `;` (分号) | `C:\path1;C:\path2;C:\path3` |

**跨平台代码**：

```python
import os

# 使用 os.pathsep 自动选择正确的分隔符
paths = ['/path1', '/path2', '/path3']
pythonpath = os.pathsep.join(paths)
os.environ['PYTHONPATH'] = pythonpath
```

---

### ⚠️ 2. 优先级问题

PYTHONPATH 的优先级**高于** site-packages，可能导致版本冲突：

```bash
# 场景：已安装 mypackage 1.0
pip install mypackage==1.0

# 但 PYTHONPATH 指向开发版本 2.0
export PYTHONPATH=/path/to/mypackage-dev-2.0

# Python 会使用 2.0 版本，而不是已安装的 1.0
python -c "import mypackage; print(mypackage.__version__)"  # 输出: 2.0
```

**解决方案**：
- 使用虚拟环境隔离
- 明确知道自己在做什么
- 测试完成后取消设置

---

### ⚠️ 3. 相对路径 vs 绝对路径

**推荐使用绝对路径**：

```bash
# ✅ 好：绝对路径，不依赖当前目录
export PYTHONPATH=/Users/songji/Code/Python/my_project

# ❌ 不推荐：相对路径，依赖当前工作目录
export PYTHONPATH=./my_project
export PYTHONPATH=../other_project
```

**原因**：相对路径会根据当前工作目录变化，导致不可预测的行为。

---

### ⚠️ 4. 不要滥用

**不推荐**：
```bash
# ❌ 将所有项目都加到 PYTHONPATH
export PYTHONPATH=/project1:/project2:/project3:/project4:/project5
```

**推荐**：
```bash
# ✅ 使用虚拟环境和可编辑安装
python -m venv venv
source venv/bin/activate
pip install -e /project1
pip install -e /project2
```

---

### ⚠️ 5. 环境变量作用域

```bash
# 仅在当前终端会话有效
export PYTHONPATH=/path/to/modules

# 新开的终端不会有这个设置
# 需要重新设置或写入配置文件
```

---

## 最佳实践

### ✅ 1. 开发环境：使用可编辑安装

**推荐方式**：

```bash
# 进入项目目录
cd /path/to/my_project

# 可编辑安装（开发模式）
pip install -e .

# 优点：
# - 代码修改立即生效
# - 自动处理依赖
# - 注册 Entry Points
# - 不需要设置 PYTHONPATH
```

**对比**：

| 特性 | PYTHONPATH | pip install -e | pip install |
|------|-----------|----------------|-------------|
| 设置复杂度 | 简单 | 中等 | 简单 |
| 持久性 | 临时 | 永久 | 永久 |
| 依赖处理 | ❌ | ✅ | ✅ |
| Entry Points | ❌ | ✅ | ✅ |
| 代码修改生效 | ✅ 立即 | ✅ 立即 | ❌ 需重装 |
| 适用场景 | 快速测试 | 开发调试 | 生产环境 |

---

### ✅ 2. 使用虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# 在虚拟环境中安装包
pip install -e .

# 优点：
# - 隔离项目依赖
# - 避免版本冲突
# - 不污染全局环境
```

---

### ✅ 3. 项目配置文件

创建 `.env` 文件：

```bash
# .env
PYTHONPATH=/path/to/project/src:/path/to/shared/libs
```

使用 `python-dotenv` 加载：

```python
# main.py
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()

# 现在可以使用环境变量
print(os.environ.get('PYTHONPATH'))
```

---

### ✅ 4. 文档化

在项目的 `README.md` 中说明：

```markdown
## 开发环境设置

### 方式 1：使用 PYTHONPATH（快速测试）

```bash
export PYTHONPATH=/path/to/project/src
python test_script.py
```

### 方式 2：可编辑安装（推荐）

```bash
pip install -e .
python test_script.py
```
```

---

### ✅ 5. 调试技巧

```python
# 在脚本开头添加调试代码
import sys
print("Python 搜索路径:")
for i, path in enumerate(sys.path, 1):
    print(f"  {i}. {path}")

# 检查模块来源
import mymodule
print(f"mymodule 位置: {mymodule.__file__}")
```

---

## 常见问题

### Q1: PYTHONPATH 设置后不生效？

**可能原因**：

1. **拼写错误**：
   ```bash
   # ❌ 错误
   export PYTHON_PATH=/path/to/modules
   
   # ✅ 正确
   export PYTHONPATH=/path/to/modules
   ```

2. **路径不存在**：
   ```bash
   # 检查路径是否存在
   ls -la /path/to/modules
   ```

3. **分隔符错误**：
   ```bash
   # ❌ Linux 上使用分号
   export PYTHONPATH=/path1;/path2
   
   # ✅ Linux 上使用冒号
   export PYTHONPATH=/path1:/path2
   ```

4. **在错误的 shell 中设置**：
   ```bash
   # 检查当前 shell
   echo $SHELL
   
   # 确保在正确的配置文件中设置
   # Bash: ~/.bashrc
   # Zsh: ~/.zshrc
   ```

---

### Q2: 如何查看当前 PYTHONPATH？

```bash
# 方法 1：查看环境变量
echo $PYTHONPATH

# 方法 2：在 Python 中查看
python -c "import os; print(os.environ.get('PYTHONPATH', '未设置'))"

# 方法 3：查看完整搜索路径
python -c "import sys; print('\n'.join(sys.path))"
```

---

### Q3: 如何临时取消 PYTHONPATH？

```bash
# 方法 1：取消设置
unset PYTHONPATH

# 方法 2：设置为空
export PYTHONPATH=

# 方法 3：在命令中临时取消
env -u PYTHONPATH python script.py
```

---

### Q4: PYTHONPATH 和 sys.path 的区别？

| 特性 | PYTHONPATH | sys.path |
|------|-----------|----------|
| 类型 | 环境变量 | Python 列表 |
| 设置时机 | Python 启动前 | Python 运行时 |
| 作用域 | 进程级别 | 当前 Python 进程 |
| 持久性 | 可永久（配置文件） | 临时（脚本运行期间） |
| 修改方式 | `export PYTHONPATH=...` | `sys.path.append(...)` |

**关系**：
- PYTHONPATH 的内容会被添加到 `sys.path` 中
- `sys.path` 包含更多路径（标准库、site-packages 等）

---

### Q5: 为什么不推荐在生产环境使用 PYTHONPATH？

**原因**：

1. **不可靠**：依赖环境变量，容易被覆盖或遗忘
2. **难以管理**：多个项目可能冲突
3. **不处理依赖**：无法自动安装依赖包
4. **难以部署**：需要在每个环境中手动设置

**推荐方案**：

```bash
# 开发环境
pip install -e .

# 生产环境
pip install .
# 或
pip install package-name==1.0.0
```

---

### Q6: 如何在 IDE 中设置 PYTHONPATH？

#### PyCharm

1. File → Settings → Project → Project Structure
2. 右键目录 → Mark Directory as → Sources Root

或者：

1. Run → Edit Configurations
2. Environment variables → 添加 `PYTHONPATH=/path/to/modules`

#### VS Code

编辑 `.vscode/settings.json`：

```json
{
    "python.analysis.extraPaths": [
        "/path/to/modules"
    ],
    "terminal.integrated.env.osx": {
        "PYTHONPATH": "/path/to/modules"
    }
}
```

---

## 总结

### 核心要点

1. **PYTHONPATH** 是一个环境变量，用于添加额外的模块搜索路径
2. 适用于**快速测试**和**临时开发**
3. **不推荐**在生产环境使用
4. **推荐**使用 `pip install -e .` 进行开发

### 使用决策树

```
需要导入自定义模块？
├─ 是生产环境？
│  └─ 使用 pip install
├─ 是开发环境？
│  ├─ 需要频繁修改代码？
│  │  └─ 使用 pip install -e .
│  └─ 只是快速测试？
│     └─ 使用 PYTHONPATH
└─ 是共享工具库？
   └─ 考虑创建独立包并安装
```

### 快速参考

```bash
# 临时设置（当前会话）
export PYTHONPATH=/path/to/modules

# 永久设置（添加到 ~/.zshrc）
echo 'export PYTHONPATH=/path/to/modules:$PYTHONPATH' >> ~/.zshrc
source ~/.zshrc

# 查看当前设置
echo $PYTHONPATH

# 取消设置
unset PYTHONPATH

# 一次性使用
PYTHONPATH=/path/to/modules python script.py
```

---

## 参考资源

- [Python 官方文档 - sys.path](https://docs.python.org/3/library/sys.html#sys.path)
- [Python 官方文档 - PYTHONPATH](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPATH)
- [PEP 420 - Implicit Namespace Packages](https://www.python.org/dev/peps/pep-0420/)

---

**文档版本**: 1.0  
**最后更新**: 2026-01-14  
**适用于**: Python 3.6+
