# OpenTelemetry MyCache Instrumentation

这是一个教学性质的 OpenTelemetry Python 埋点插件，用于演示如何为 Python 库创建 Instrumentation。

---

## 📦 安装步骤

### 方式一：本地开发安装（推荐学习使用）

```bash
# 1. 进入插件目录
cd instrumentation/opentelemetry-instrumentation-demo-mycache

# 2. 以开发模式安装（-e 表示 editable，修改代码后无需重新安装）
pip install -e .
```

### 方式二：直接安装（如果已发布到 PyPI）

```bash
pip install opentelemetry-instrumentation-demo-mycache
```

### 方式三：从源码安装

```bash
pip install git+https://github.com/your-repo/opentelemetry-python-contrib.git#subdirectory=instrumentation/opentelemetry-instrumentation-demo-mycache
```

---

## 🔧 前置依赖

确保已安装 OpenTelemetry SDK：

```bash
# 核心依赖
pip install opentelemetry-api opentelemetry-sdk

# 如果需要导出到 Jaeger/Zipkin 等后端
pip install opentelemetry-exporter-jaeger
# 或
pip install opentelemetry-exporter-otlp
```

---

## 🚀 使用方式

### 方式一：手动调用 instrument()（显式埋点）

这是最基础的使用方式，适合需要精细控制的场景：

```python
# app.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# ============================================
# 第一步：配置 OpenTelemetry（必须在 instrument 之前）
# ============================================
# 创建 TracerProvider
provider = TracerProvider()

# 添加导出器（这里用控制台输出，生产环境换成 Jaeger/OTLP 等）
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)

# 设置全局 TracerProvider
trace.set_tracer_provider(provider)

# ============================================
# 第二步：启用埋点插件
# ============================================
from opentelemetry.instrumentation.demo_mycache import MyCacheInstrumentor

# 调用 instrument() 启用埋点
MyCacheInstrumentor().instrument()

# ============================================
# 第三步：正常使用 mycache 库（自动产生 Span）
# ============================================
from mycache import MyCache

cache = MyCache()
cache.set("user:1001", {"name": "张三", "age": 25})  # 自动创建 Span
value = cache.get("user:1001")                       # 自动创建 Span
print(f"获取到: {value}")
```

### 方式二：使用 opentelemetry-instrument 命令（自动埋点）

这是推荐的生产环境使用方式，无需修改代码：

```bash
# 1. 安装自动埋点工具
pip install opentelemetry-distro opentelemetry-instrumentation

# 2. 安装所有可用的埋点插件（会自动发现已安装的插件）
opentelemetry-bootstrap -a install

# 3. 使用 opentelemetry-instrument 命令启动你的应用
opentelemetry-instrument \
    --traces_exporter console \
    --service_name my-app \
    python app.py
```

**原理说明**：
- `opentelemetry-instrument` 会自动扫描 `entry_points` 中注册的所有插件
- 检测 `mycache` 库是否已安装且版本符合要求
- 如果满足条件，自动调用 `MyCacheInstrumentor().instrument()`

---

### ❓ `opentelemetry-bootstrap -a install` 会发现我的插件吗？

**答案：会，但前提是你的插件已经安装到当前 Python 环境中。**

#### 发现机制详解

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     opentelemetry-bootstrap 发现流程                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  1. 扫描 Entry Points                                                           │
│     ┌─────────────────────────────────────────────────────────────────────┐     │
│     │ 遍历 Python 环境中所有包的 entry_points                               │     │
│     │ 寻找 group = "opentelemetry_instrumentor" 的入口点                   │     │
│     └─────────────────────────────────────────────────────────────────────┘     │
│                                    ↓                                            │
│  2. 检查目标库依赖                                                               │
│     ┌─────────────────────────────────────────────────────────────────────┐     │
│     │ 读取插件 pyproject.toml 中的 instruments = ["mycache >= 1.0.0"]     │     │
│     │ 检查 mycache 是否已安装且版本符合要求                                  │     │
│     └─────────────────────────────────────────────────────────────────────┘     │
│                                    ↓                                            │
│  3. 输出/安装                                                                    │
│     ┌─────────────────────────────────────────────────────────────────────┐     │
│     │ -a install: 安装所有满足条件的插件                                     │     │
│     │ 无参数: 只列出可安装的插件                                             │     │
│     └─────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### 你的插件被发现的条件

```bash
# 条件 1：插件已安装到当前环境
pip install opentelemetry-instrumentation-demo-mycache
# 或者本地开发安装
pip install -e ./instrumentation/opentelemetry-instrumentation-demo-mycache

# 条件 2：pyproject.toml 中正确配置了 entry_points
[project.entry-points.opentelemetry_instrumentor]
demo_mycache = "opentelemetry.instrumentation.demo_mycache:MyCacheInstrumentor"

# 条件 3：目标库 mycache 已安装（bootstrap 时检查）
pip install mycache
```

#### 验证插件是否被发现

```bash
# 查看所有可发现的插件（不安装）
opentelemetry-bootstrap

# 输出示例：
# opentelemetry-instrumentation-redis>=0.40b0
# opentelemetry-instrumentation-flask>=0.40b0
# opentelemetry-instrumentation-demo-mycache>=0.1.0  <-- 你的插件出现在这里就成功了！
```

---

### 🎯 如何只安装特定插件（而不是全部）？

`opentelemetry-bootstrap -a install` 会安装**所有**检测到的插件，但有时你只想安装特定的几个。

#### 方法一：直接 pip install（推荐）

```bash
# 只安装你需要的插件
pip install opentelemetry-instrumentation-demo-mycache
pip install opentelemetry-instrumentation-redis

# 不要运行 opentelemetry-bootstrap -a install
```

#### 方法二：使用 bootstrap 列出后手动选择

```bash
# 1. 先列出所有可用插件
opentelemetry-bootstrap

# 输出：
# opentelemetry-instrumentation-redis>=0.40b0
# opentelemetry-instrumentation-flask>=0.40b0
# opentelemetry-instrumentation-django>=0.40b0
# opentelemetry-instrumentation-demo-mycache>=0.1.0

# 2. 手动安装你需要的
pip install opentelemetry-instrumentation-redis opentelemetry-instrumentation-demo-mycache
```

#### 方法三：使用 requirements.txt 管理

```txt
# requirements-otel.txt
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation==0.42b0

# 只列出需要的插件
opentelemetry-instrumentation-redis==0.42b0
opentelemetry-instrumentation-demo-mycache==0.1.0
# 注意：不要加 opentelemetry-instrumentation-flask 等不需要的
```

```bash
pip install -r requirements-otel.txt
```

#### 方法四：运行时禁用不需要的插件

如果已经安装了所有插件，可以在运行时禁用：

```bash
# 通过环境变量禁用特定插件
export OTEL_PYTHON_DISABLED_INSTRUMENTATIONS="flask,django"

# 或者在命令行中指定
opentelemetry-instrument \
    --disabled_instrumentations flask,django \
    python app.py
```

---

### 🆚 与 Java 自动发现对比

| 特性 | Java (Agent) | Python (bootstrap) |
|------|--------------|-------------------|
| **发现机制** | SPI (`META-INF/services/`) | Entry Points (`pyproject.toml`) |
| **安装全部** | 打包进 agent jar | `opentelemetry-bootstrap -a install` |
| **选择性安装** | 通常打包时决定 | `pip install` 单个插件 |
| **运行时禁用** | `-Dotel.instrumentation.[NAME].enabled=false` | `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` |
| **依赖检测** | 类加载时检查 | `packaging` 库检查版本 |

**Java 示例**（对比）：
```bash
# Java: 通过系统属性禁用
java -javaagent:opentelemetry-javaagent.jar \
     -Dotel.instrumentation.redis.enabled=false \
     -jar app.jar

# Python: 通过环境变量禁用
OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=redis \
opentelemetry-instrument python app.py
```

### 方式三：只对特定实例埋点

如果不想对所有 MyCache 实例生效，可以只对特定实例埋点：

```python
from mycache import MyCache
from opentelemetry.instrumentation.demo_mycache import MyCacheInstrumentor

# 创建实例
cache1 = MyCache()  # 这个不会被埋点
cache2 = MyCache()  # 这个会被埋点

# 只对 cache2 启用埋点
MyCacheInstrumentor().instrument_client(cache2)

cache1.get("key")  # 不产生 Span
cache2.get("key")  # 产生 Span
```

---

## ⚙️ 高级配置

### 1. 使用 Hook 自定义属性

```python
def my_request_hook(span, instance, args, kwargs):
    """请求开始时调用，可以添加自定义属性"""
    span.set_attribute("custom.cache_size", len(instance._store))
    span.set_attribute("custom.operation_args", str(args))

def my_response_hook(span, instance, response):
    """请求结束时调用，可以记录响应信息"""
    span.set_attribute("custom.response_type", type(response).__name__)
    if response is None:
        span.set_attribute("custom.cache_hit", False)
    else:
        span.set_attribute("custom.cache_hit", True)

# 启用埋点时传入 hook
MyCacheInstrumentor().instrument(
    request_hook=my_request_hook,
    response_hook=my_response_hook
)
```

### 2. 通过环境变量配置

```bash
# 禁用特定插件
export OTEL_PYTHON_DISABLED_INSTRUMENTATIONS="demo-mycache,redis"

# 设置服务名
export OTEL_SERVICE_NAME="my-cache-service"

# 设置导出器
export OTEL_TRACES_EXPORTER="jaeger"
export OTEL_EXPORTER_JAEGER_ENDPOINT="http://localhost:14268/api/traces"
```

### 3. 卸载埋点

```python
# 如果需要动态关闭埋点
MyCacheInstrumentor().uninstrument()
```

---

## 📊 生成的 Span 属性

每个操作会生成一个 `CLIENT` 类型的 Span，包含以下属性：

| 属性名 | 说明 | 示例值 |
|--------|------|--------|
| `db.system` | 数据库系统类型 | `"mycache"` |
| `db.operation` | 操作类型 | `"GET"`, `"SET"`, `"DELETE"` |
| `db.statement` | 完整命令 | `"GET user:1001"` |
| `net.peer.name` | 服务地址 | `"localhost"` |
| `net.peer.port` | 服务端口 | `6379` |

---

## 🔍 验证埋点是否生效

### 方法一：使用控制台导出器

```python
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
```

运行后会在控制台看到类似输出：

```json
{
    "name": "GET",
    "context": {
        "trace_id": "0x5ce0bf87...",
        "span_id": "0x7f1a2b3c..."
    },
    "kind": "SpanKind.CLIENT",
    "attributes": {
        "db.system": "mycache",
        "db.operation": "GET",
        "db.statement": "GET user:1001"
    }
}
```

### 方法二：使用 Jaeger UI 查看

```bash
# 启动 Jaeger
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest

# 配置导出到 Jaeger
pip install opentelemetry-exporter-jaeger
```

```python
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
provider.add_span_processor(SimpleSpanProcessor(exporter))
```

访问 http://localhost:16686 查看 Trace。

---

## 🆚 与 Java 使用方式对比

| 步骤 | Java | Python |
|------|------|--------|
| **安装依赖** | 添加 Maven/Gradle 依赖 | `pip install opentelemetry-instrumentation-xxx` |
| **自动埋点** | `-javaagent:opentelemetry-javaagent.jar` | `opentelemetry-instrument python app.py` |
| **手动埋点** | 代码中调用 `GlobalOpenTelemetry.get()` | 代码中调用 `Instrumentor().instrument()` |
| **配置方式** | 系统属性 `-Dotel.xxx` | 环境变量 `OTEL_XXX` |
| **禁用插件** | `-Dotel.instrumentation.xxx.enabled=false` | `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=xxx` |

---

## 📁 项目结构说明

```
opentelemetry-instrumentation-demo-mycache/
├── pyproject.toml              # 项目配置，声明依赖和 entry_points
├── README.md                   # 本文档
├── src/
│   └── opentelemetry/
│       └── instrumentation/
│           └── demo_mycache/
│               ├── __init__.py     # 核心实现（包含详细教学注释）
│               ├── version.py      # 版本号
│               └── package.py      # 依赖声明
└── tests/
    ├── mock_mycache.py         # 模拟的 mycache 库
    └── demo_usage.py           # 使用示例
```

---

## ❓ 常见问题

### Q: 为什么埋点没有生效？

1. **检查是否配置了 TracerProvider**：
   ```python
   from opentelemetry import trace
   print(trace.get_tracer_provider())  # 不应该是 NoOpTracerProvider
   ```

2. **检查 instrument() 是否在使用库之前调用**：
   ```python
   # ✅ 正确顺序
   MyCacheInstrumentor().instrument()
   from mycache import MyCache
   
   # ❌ 错误顺序（已导入的模块不会被重新包装）
   from mycache import MyCache
   MyCacheInstrumentor().instrument()
   ```

3. **检查是否被禁用**：
   ```bash
   echo $OTEL_PYTHON_DISABLED_INSTRUMENTATIONS
   ```

### Q: 如何查看所有已安装的插件？

```bash
opentelemetry-bootstrap --action=requirements
```

### Q: 如何只导出特定操作的 Span？

使用 Sampler：
```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

provider = TracerProvider(sampler=TraceIdRatioBased(0.1))  # 只采样 10%
```

---

## 🚢 发布到 PyPI

将你的埋点插件发布到 PyPI，让其他人可以通过 `pip install` 安装。

### 前置准备

```bash
# 1. 安装构建和发布工具
pip install build twine

# 2. 注册 PyPI 账号
#    - 正式环境：https://pypi.org/account/register/
#    - 测试环境：https://test.pypi.org/account/register/（推荐先在这里测试）

# 3. 创建 API Token（推荐，比密码更安全）
#    登录 PyPI -> Account Settings -> API tokens -> Add API token
```

### 发布步骤

#### 步骤一：检查 pyproject.toml 配置

确保 `pyproject.toml` 中的元数据正确：

```toml
[project]
name = "opentelemetry-instrumentation-demo-mycache"  # 包名（必须唯一）
version = "0.1.0"                                      # 版本号
description = "OpenTelemetry MyCache Instrumentation"
readme = "README.md"
license = {text = "Apache-2.0"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
keywords = ["opentelemetry", "instrumentation", "tracing", "mycache"]

[project.urls]
Homepage = "https://github.com/your-org/opentelemetry-python-contrib"
Repository = "https://github.com/your-org/opentelemetry-python-contrib"
```

#### 步骤二：构建包

```bash
# 进入项目目录
cd instrumentation/opentelemetry-instrumentation-demo-mycache

# 清理旧的构建文件
rm -rf dist/ build/ *.egg-info src/*.egg-info

# 构建 sdist（源码包）和 wheel（二进制包）
python -m build

# 构建完成后，dist/ 目录下会有两个文件：
# - opentelemetry_instrumentation_demo_mycache-0.1.0.tar.gz  (sdist)
# - opentelemetry_instrumentation_demo_mycache-0.1.0-py3-none-any.whl  (wheel)
```

#### 步骤三：检查包内容（可选但推荐）

```bash
# 检查包的元数据是否正确
twine check dist/*

# 查看包内容
tar -tzf dist/*.tar.gz
unzip -l dist/*.whl
```

#### 步骤四：发布到 TestPyPI（推荐先测试）

```bash
# 发布到测试环境
twine upload --repository testpypi dist/*

# 输入用户名：__token__
# 输入密码：你的 API Token（以 pypi- 开头）

# 测试安装
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    opentelemetry-instrumentation-demo-mycache
```

#### 步骤五：发布到正式 PyPI

```bash
# 确认测试无误后，发布到正式环境
twine upload dist/*

# 输入用户名：__token__
# 输入密码：你的 API Token
```

### 使用 .pypirc 简化认证（可选）

创建 `~/.pypirc` 文件避免每次输入 Token：

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-api-token-here

[testpypi]
username = __token__
password = pypi-your-test-api-token-here
```

```bash
# 设置权限（重要！防止 Token 泄露）
chmod 600 ~/.pypirc
```

### 版本更新发布

每次更新版本时：

```bash
# 1. 修改版本号
# 编辑 src/opentelemetry/instrumentation/demo_mycache/version.py
__version__ = "0.2.0"

# 2. 同步修改 pyproject.toml 中的版本
# version = "0.2.0"

# 3. 清理、构建、发布
rm -rf dist/ build/
python -m build
twine upload dist/*
```

### 🆚 与 Java 发布对比

| 步骤 | Java (Maven) | Python (PyPI) |
|------|--------------|---------------|
| **配置文件** | `pom.xml` | `pyproject.toml` |
| **仓库** | Maven Central / Nexus | PyPI |
| **构建命令** | `mvn package` | `python -m build` |
| **发布命令** | `mvn deploy` | `twine upload dist/*` |
| **认证方式** | `settings.xml` 或 GPG 签名 | API Token |
| **版本管理** | `<version>` 标签 | `version.py` + `pyproject.toml` |
| **依赖声明** | `<dependencies>` | `[project.dependencies]` |
| **入口点** | `META-INF/services/` (SPI) | `[project.entry-points]` |

### 自动化发布（CI/CD）

#### GitHub Actions 示例

创建 `.github/workflows/publish.yml`：

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine
      
      - name: Build package
        working-directory: instrumentation/opentelemetry-instrumentation-demo-mycache
        run: python -m build
      
      - name: Publish to PyPI
        working-directory: instrumentation/opentelemetry-instrumentation-demo-mycache
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

**配置说明**：
1. 在 GitHub 仓库的 Settings -> Secrets 中添加 `PYPI_API_TOKEN`
2. 创建 Release 时自动触发发布

### 发布检查清单

发布前确保完成以下检查：

- [ ] 版本号已更新（`version.py` 和 `pyproject.toml`）
- [ ] README 文档已更新
- [ ] 所有测试通过：`pytest tests/`
- [ ] 代码格式化：`black src/` 和 `isort src/`
- [ ] 类型检查通过：`mypy src/`
- [ ] `twine check dist/*` 无警告
- [ ] 在 TestPyPI 测试安装成功
- [ ] CHANGELOG 已更新（如果有的话）

---

## 📚 相关资源

- [OpenTelemetry Python 官方文档](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry Python Contrib 仓库](https://github.com/open-telemetry/opentelemetry-python-contrib)
- [OpenTelemetry 语义规范](https://opentelemetry.io/docs/specs/semconv/)
- [PyPI 发布指南](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [Python 打包用户指南](https://packaging.python.org/)
