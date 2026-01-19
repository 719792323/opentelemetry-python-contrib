# OpenTelemetry Python Contrib 项目分析指南

> 本文档专为有 OpenTelemetry Java 开发经验的开发者编写，帮助快速理解 Python 版本的实现

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 目录结构详解](#2-目录结构详解)
- [3. 与Java版本的核心差异对比](#3-与java版本的核心差异对比)
- [4. 核心概念与组件](#4-核心概念与组件)
- [5. Demo教程](#5-demo教程)
- [6. 如何开发自定义Instrumentation](#6-如何开发自定义instrumentation)

---

## 1. 项目概述

**opentelemetry-python-contrib** 是 OpenTelemetry Python 的扩展项目，提供：
- 🔧 **自动化Instrumentation**：为流行的Python库（Flask、Django、requests等）提供开箱即用的埋点
- 🌐 **Propagator**：上下文传播器（如AWS X-Ray格式）
- 📤 **Exporter**：数据导出器
- 🔌 **SDK扩展**：SDK功能增强（如AWS X-Ray ID生成器）
- 🤖 **GenAI Instrumentation**：AI/ML框架的观测支持

### 核心仓库关系
```
opentelemetry-python (核心API/SDK)
        ↓
opentelemetry-python-contrib (本项目 - 扩展与Instrumentation)
```

---

## 2. 目录结构详解

```
opentelemetry-python-contrib/
│
├── instrumentation/                    # ⭐ 核心: 各种库的自动化埋点实现
│   ├── opentelemetry-instrumentation-flask/
│   ├── opentelemetry-instrumentation-django/
│   ├── opentelemetry-instrumentation-requests/
│   ├── opentelemetry-instrumentation-fastapi/
│   ├── opentelemetry-instrumentation-redis/
│   ├── opentelemetry-instrumentation-celery/
│   └── ... (50+ instrumentation 模块)
│
├── instrumentation-genai/              # AI/ML框架的Instrumentation
│   ├── opentelemetry-instrumentation-openai-v2/
│   ├── opentelemetry-instrumentation-langchain/
│   ├── opentelemetry-instrumentation-anthropic/
│   └── opentelemetry-instrumentation-vertexai/
│
├── opentelemetry-instrumentation/      # ⭐ Instrumentation基础框架
│   └── src/opentelemetry/instrumentation/
│       ├── instrumentor.py            # BaseInstrumentor 抽象基类
│       ├── bootstrap.py               # 自动安装/发现机制
│       └── auto_instrumentation/      # 自动注入逻辑
│
├── propagator/                         # 上下文传播器
│   ├── opentelemetry-propagator-aws-xray/
│   └── opentelemetry-propagator-ot-trace/
│
├── sdk-extension/                      # SDK扩展
│   └── opentelemetry-sdk-extension-aws/
│       └── trace/                     # AWS X-Ray ID生成器等
│
├── exporter/                           # 数据导出器
│   ├── opentelemetry-exporter-richconsole/
│   └── opentelemetry-exporter-prometheus-remote-write/
│
├── resource/                           # 资源检测器
│   ├── opentelemetry-resource-detector-azure/
│   └── opentelemetry-resource-detector-containerid/
│
├── processor/                          # Span/Log处理器
│   └── opentelemetry-processor-baggage/
│
├── util/                               # 工具类库
│   ├── opentelemetry-util-http/       # HTTP工具
│   └── opentelemetry-util-genai/      # GenAI工具
│
├── _template/                          # 新建Instrumentation的模板
├── docs/                               # 文档
└── tests/                              # 集成测试
```

### 单个Instrumentation模块的内部结构

以 `opentelemetry-instrumentation-flask` 为例：

```
opentelemetry-instrumentation-flask/
├── pyproject.toml                      # 📦 包配置（类似Java的pom.xml/build.gradle）
├── README.rst                          # 文档
├── src/
│   └── opentelemetry/
│       └── instrumentation/
│           └── flask/
│               ├── __init__.py         # ⭐ 核心实现：FlaskInstrumentor
│               ├── package.py          # 依赖声明
│               └── version.py          # 版本号
└── tests/
    ├── test_automatic.py               # 自动注入测试
    └── test_programmatic.py            # 手动注入测试
```

---

## 3. 与Java版本的核心差异对比

### 3.1 包管理对比

| 方面 | Java | Python |
|------|------|--------|
| 构建工具 | Maven/Gradle | Hatch/pip |
| 配置文件 | `pom.xml` / `build.gradle` | `pyproject.toml` |
| 依赖安装 | `mvn install` | `pip install -e .` |
| 仓库 | Maven Central | PyPI |

### 3.2 自动注入机制对比

**Java: 使用Java Agent (-javaagent)**
```bash
java -javaagent:opentelemetry-javaagent.jar -jar myapp.jar
```

**Python: 使用opentelemetry-instrument命令**
```bash
opentelemetry-instrument python myapp.py

# 或使用 bootstrap 自动安装依赖
opentelemetry-bootstrap -a install
```

### 3.3 核心类对比

| 概念 | Java | Python |
|------|------|--------|
| Instrumenter基类 | `InstrumenterModule` | `BaseInstrumentor` |
| 方法包装 | Byte Buddy | `functools.wraps` / Monkey Patching |
| 入口点声明 | `@AutoService` | `pyproject.toml` entry_points |

### 3.4 Entry Point 配置对比

**Java (使用 @AutoService 注解)**
```java
@AutoService(InstrumentationModule.class)
public class FlaskInstrumentationModule extends InstrumentationModule {
    // ...
}
```

**Python (在 pyproject.toml 中声明)**
```toml
[project.entry-points.opentelemetry_instrumentor]
flask = "opentelemetry.instrumentation.flask:FlaskInstrumentor"
```

---

## 4. 核心概念与组件

### 4.1 BaseInstrumentor - 核心抽象类

路径: `opentelemetry-instrumentation/src/opentelemetry/instrumentation/instrumentor.py`

```python
class BaseInstrumentor(ABC):
    """所有Instrumentor的基类，类似Java的InstrumentationModule"""
    
    _instance = None  # 单例模式
    _is_instrumented_by_opentelemetry = False
    
    @abstractmethod
    def instrumentation_dependencies(self) -> Collection[str]:
        """声明被埋点库的依赖要求（类似Java的classLoaderMatcher）"""
        pass
    
    @abstractmethod
    def _instrument(self, **kwargs):
        """执行埋点逻辑"""
        pass
    
    @abstractmethod
    def _uninstrument(self, **kwargs):
        """移除埋点"""
        pass
    
    def instrument(self, **kwargs):
        """公开的instrument方法，包含冲突检测和状态管理"""
        if self._is_instrumented_by_opentelemetry:
            return  # 防止重复注入
        # 检查依赖冲突
        conflict = self._check_dependency_conflicts()
        if conflict:
            return
        self._instrument(**kwargs)
        self._is_instrumented_by_opentelemetry = True
```

### 4.2 package.py - 依赖声明

每个Instrumentation都有一个 `package.py` 文件：

```python
# flask/package.py

# 声明要埋点的库及版本要求
_instruments = ("flask >= 1.0",)

# 是否支持metrics
_supports_metrics = True

# 语义约定状态: development | stable | migration
_semconv_status = "migration"
```

### 4.3 Propagator - 上下文传播器

类似Java的 `TextMapPropagator`：

```python
from opentelemetry.propagators.aws import AwsXRayPropagator

# 注入上下文到HTTP Header
propagator = AwsXRayPropagator()
propagator.inject(carrier=headers)

# 从HTTP Header提取上下文
context = propagator.extract(carrier=headers)
```

### 4.4 ID Generator - ID生成器

类似Java的 `IdGenerator`：

```python
from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator

# 配置SDK使用AWS X-Ray兼容的ID生成器
from opentelemetry.sdk.trace import TracerProvider

provider = TracerProvider(id_generator=AwsXRayIdGenerator())
```

---

## 5. Demo教程

### 5.1 Flask 应用自动埋点

**安装依赖**
```bash
pip install flask
pip install opentelemetry-api
pip install opentelemetry-sdk
pip install opentelemetry-instrumentation-flask
pip install opentelemetry-exporter-otlp
```

**方式1: 编程式注入**
```python
# app.py
from flask import Flask
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# 1. 配置 TracerProvider
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

# 2. 创建 Flask 应用
app = Flask(__name__)

# 3. 注入 Instrumentation
FlaskInstrumentor().instrument_app(app)

@app.route("/")
def hello():
    return "Hello, OpenTelemetry!"

@app.route("/user/<user_id>")
def get_user(user_id):
    # Span会自动包含 http.route: /user/<user_id>
    return f"User: {user_id}"

if __name__ == "__main__":
    app.run(debug=True)
```

**方式2: 自动注入（推荐生产环境）**
```bash
# 使用 opentelemetry-instrument 命令运行应用
opentelemetry-instrument \
    --traces_exporter console \
    --metrics_exporter none \
    python app.py
```

**方式3: 使用Request/Response Hook自定义**
```python
from opentelemetry.trace import Span
from opentelemetry.instrumentation.flask import FlaskInstrumentor

def request_hook(span: Span, environ: dict):
    """请求开始时调用"""
    if span and span.is_recording():
        span.set_attribute("custom.user_agent", environ.get("HTTP_USER_AGENT", ""))

def response_hook(span: Span, status: str, response_headers: list):
    """响应结束时调用"""
    if span and span.is_recording():
        span.set_attribute("custom.response_status", status)

FlaskInstrumentor().instrument(
    request_hook=request_hook,
    response_hook=response_hook
)
```

### 5.2 Requests HTTP 客户端埋点

```python
import requests
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# 配置 TracerProvider
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

# 注入 requests 库
RequestsInstrumentor().instrument()

# 现在所有 requests 调用都会自动创建 Span
response = requests.get("https://httpbin.org/get")
print(response.status_code)

# 带自定义Hook
def request_hook(span, request):
    span.set_attribute("http.request.body_size", len(request.body or b""))

def response_hook(span, request, response):
    span.set_attribute("http.response.body_size", len(response.content))

RequestsInstrumentor().instrument(
    request_hook=request_hook,
    response_hook=response_hook
)
```

### 5.3 AWS X-Ray 集成示例

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator
from opentelemetry.propagators.aws import AwsXRayPropagator
from opentelemetry.propagate import set_global_textmap

# 1. 使用 AWS X-Ray ID 生成器
provider = TracerProvider(id_generator=AwsXRayIdGenerator())
trace.set_tracer_provider(provider)

# 2. 设置 AWS X-Ray 传播器
set_global_textmap(AwsXRayPropagator())

# 获取 tracer
tracer = trace.get_tracer(__name__)

# 创建 Span（ID格式兼容X-Ray）
with tracer.start_as_current_span("my-operation") as span:
    span.set_attribute("service.name", "my-service")
    # Trace ID 格式: 1-{时间戳}-{随机ID}
    print(f"Trace ID: {span.get_span_context().trace_id:032x}")
```

### 5.4 Django 应用埋点

```python
# settings.py
INSTALLED_APPS = [
    # ... 其他应用
]

# 配置 OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.django import DjangoInstrumentor

provider = TracerProvider()
trace.set_tracer_provider(provider)

# 在 Django 启动时注入
DjangoInstrumentor().instrument()

# 或者使用环境变量配置
# DJANGO_SETTINGS_MODULE=myapp.settings
# OTEL_PYTHON_DJANGO_INSTRUMENT=true
```

### 5.5 数据库埋点示例 (PostgreSQL)

```python
import psycopg2
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

# 注入 psycopg2
Psycopg2Instrumentor().instrument()

# 正常使用数据库
conn = psycopg2.connect("dbname=test user=postgres")
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE id = %s", (1,))
# 会自动创建 db.statement Span

# 启用 SQL Commenter（在SQL中添加追踪上下文注释）
Psycopg2Instrumentor().instrument(enable_commenter=True)
# SQL会变成: SELECT * FROM users WHERE id = %s /*traceparent=00-xxx-xxx-01*/
```

### 5.6 完整的分布式追踪示例

```python
# service_a.py - Web服务
from flask import Flask
import requests
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat

# 配置
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
set_global_textmap(B3MultiFormat())

# 注入
FlaskInstrumentor().instrument()
RequestsInstrumentor().instrument()

app = Flask(__name__)

@app.route("/")
def index():
    # 调用下游服务 - 上下文会自动传播
    response = requests.get("http://localhost:5001/downstream")
    return f"Service A received: {response.text}"

if __name__ == "__main__":
    app.run(port=5000)
```

```python
# service_b.py - 下游服务
from flask import Flask
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat

# 相同配置
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
set_global_textmap(B3MultiFormat())

FlaskInstrumentor().instrument()

app = Flask(__name__)

@app.route("/downstream")
def downstream():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("process-data") as span:
        span.set_attribute("processing.type", "downstream")
        return "Hello from Service B!"

if __name__ == "__main__":
    app.run(port=5001)
```

---

## 6. 如何开发自定义Instrumentation

### 6.1 目录结构

```
opentelemetry-instrumentation-mycache/
├── pyproject.toml
├── src/
│   └── opentelemetry/
│       └── instrumentation/
│           └── mycache/
│               ├── __init__.py
│               ├── package.py
│               └── version.py
└── tests/
    └── test_mycache.py
```

### 6.2 pyproject.toml 配置

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "opentelemetry-instrumentation-mycache"
dynamic = ["version"]
description = "MyCache instrumentation for OpenTelemetry"
requires-python = ">=3.9"
dependencies = [
    "opentelemetry-api ~= 1.12",
    "opentelemetry-instrumentation == 0.61b0.dev",
    "opentelemetry-semantic-conventions == 0.61b0.dev",
]

[project.optional-dependencies]
instruments = ["mycache >= 1.0"]

[project.entry-points.opentelemetry_instrumentor]
mycache = "opentelemetry.instrumentation.mycache:MyCacheInstrumentor"

[tool.hatch.version]
path = "src/opentelemetry/instrumentation/mycache/version.py"

[tool.hatch.build.targets.wheel]
packages = ["src/opentelemetry"]
```

### 6.3 核心实现

```python
# __init__.py
from typing import Collection
from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.mycache.package import _instruments
from opentelemetry.instrumentation.mycache.version import __version__
import mycache  # 假设这是要埋点的库
import functools

class MyCacheInstrumentor(BaseInstrumentor):
    """MyCache库的OpenTelemetry Instrumentor"""
    
    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments
    
    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        tracer = trace.get_tracer(
            __name__, 
            __version__, 
            tracer_provider
        )
        
        # 保存原始方法
        self._original_get = mycache.Client.get
        self._original_set = mycache.Client.set
        
        # 包装 get 方法
        @functools.wraps(mycache.Client.get)
        def wrapped_get(client_self, key, *args, **kwargs):
            with tracer.start_as_current_span(
                "mycache.get",
                kind=trace.SpanKind.CLIENT
            ) as span:
                span.set_attribute("db.system", "mycache")
                span.set_attribute("db.operation", "get")
                span.set_attribute("cache.key", key)
                try:
                    result = self._original_get(client_self, key, *args, **kwargs)
                    span.set_attribute("cache.hit", result is not None)
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        # 包装 set 方法
        @functools.wraps(mycache.Client.set)
        def wrapped_set(client_self, key, value, *args, **kwargs):
            with tracer.start_as_current_span(
                "mycache.set",
                kind=trace.SpanKind.CLIENT
            ) as span:
                span.set_attribute("db.system", "mycache")
                span.set_attribute("db.operation", "set")
                span.set_attribute("cache.key", key)
                try:
                    return self._original_set(client_self, key, value, *args, **kwargs)
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        # 应用 Monkey Patch
        mycache.Client.get = wrapped_get
        mycache.Client.set = wrapped_set
    
    def _uninstrument(self, **kwargs):
        # 恢复原始方法
        mycache.Client.get = self._original_get
        mycache.Client.set = self._original_set
```

### 6.4 package.py

```python
# package.py
_instruments = ("mycache >= 1.0",)
_supports_metrics = False
_semconv_status = "development"
```

### 6.5 version.py

```python
# version.py
__version__ = "0.1.0"
```

---

## 附录

### 常用环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `OTEL_SERVICE_NAME` | 服务名称 | `my-service` |
| `OTEL_TRACES_EXPORTER` | Trace导出器 | `otlp`, `console`, `none` |
| `OTEL_METRICS_EXPORTER` | Metrics导出器 | `otlp`, `console`, `none` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP端点 | `http://localhost:4317` |
| `OTEL_PYTHON_FLASK_EXCLUDED_URLS` | 排除的URL | `health,ready` |
| `OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST` | 捕获请求头 | `content-type,x-*` |

### 常用命令

```bash
# 安装所有已安装库对应的instrumentation
opentelemetry-bootstrap -a install

# 列出需要的instrumentation
opentelemetry-bootstrap -a requirements

# 自动注入运行应用
opentelemetry-instrument python app.py

# 开发模式安装
pip install -e ./instrumentation/opentelemetry-instrumentation-flask

# 运行测试
pytest instrumentation/opentelemetry-instrumentation-flask/tests/
```

### 参考链接

- [OpenTelemetry Python 官方文档](https://opentelemetry.io/docs/instrumentation/python/)
- [OpenTelemetry Python API 文档](https://opentelemetry-python-contrib.readthedocs.io/)
- [语义约定规范](https://github.com/open-telemetry/semantic-conventions)
- [OpenTelemetry Python 核心库](https://github.com/open-telemetry/opentelemetry-python)

---

*文档版本: 1.0 | 最后更新: 2024*
