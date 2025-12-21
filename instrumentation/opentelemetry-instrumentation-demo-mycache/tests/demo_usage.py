#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
OpenTelemetry Demo MyCache Instrumentation - 完整演示脚本
==============================================================================

本脚本展示 Python OT Instrumentation 的完整工作流程，并与 Java 进行对比说明。

【运行方式】
python tests/demo_usage.py

【前置条件】
1. 安装依赖：pip install opentelemetry-sdk opentelemetry-exporter-otlp wrapt
2. 确保在项目目录下运行
"""

import sys
import os

# 添加路径以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
sys.path.insert(0, os.path.dirname(__file__))

# 将 mock_mycache 模块作为 mycache 导入
import mock_mycache as mycache
sys.modules["mycache"] = mycache
sys.modules["mycache.asyncio"] = mycache.asyncio


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_section(title: str):
    print(f"\n{'─' * 40}")
    print(f" {title}")
    print(f"{'─' * 40}")


# =============================================================================
# 第一部分：OT SDK 初始化
# =============================================================================
# 【与 Java 对比】
# 
# Java Agent 方式：
#   java -javaagent:opentelemetry-javaagent.jar -jar app.jar
#   # SDK 由 agent 自动配置
#
# Java 手动方式：
#   SdkTracerProvider tracerProvider = SdkTracerProvider.builder()
#       .addSpanProcessor(SimpleSpanProcessor.create(OtlpGrpcSpanExporter.create()))
#       .build();
#   OpenTelemetrySdk.builder()
#       .setTracerProvider(tracerProvider)
#       .buildAndRegisterGlobal();
#
# Python 手动方式（如下）：

print_header("第一部分：初始化 OpenTelemetry SDK")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

# 创建资源（服务标识）
resource = Resource.create({
    "service.name": "demo-mycache-service",
    "service.version": "1.0.0",
})

# 创建 TracerProvider
# 【与 Java 对比】相当于 SdkTracerProvider.builder()
provider = TracerProvider(resource=resource)

# 添加 SpanProcessor 和 Exporter
# 这里使用 ConsoleSpanExporter 输出到控制台，方便查看
# 【与 Java 对比】相当于 .addSpanProcessor(SimpleSpanProcessor.create(...))
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

# 设置全局 TracerProvider
# 【与 Java 对比】相当于 .buildAndRegisterGlobal()
trace.set_tracer_provider(provider)

print("✓ TracerProvider 已配置，Span 将输出到控制台")


# =============================================================================
# 第二部分：导入并配置 Instrumentor
# =============================================================================

print_header("第二部分：配置 Instrumentation")

from opentelemetry.instrumentation.demo_mycache import MyCacheInstrumentor

# 演示 Hook 机制
def my_request_hook(span, instance, args, kwargs):
    """
    请求前回调
    
    【与 Java 对比】
    类似 @Advice.OnMethodEnter 中的扩展逻辑
    """
    if span and span.is_recording():
        # 添加自定义属性
        span.set_attribute("custom.hook.type", "request")
        span.set_attribute("custom.instance.host", getattr(instance, "host", "unknown"))
        print(f"  [request_hook] 触发，args={args}")


def my_response_hook(span, instance, response):
    """
    响应后回调
    
    【与 Java 对比】
    类似 @Advice.OnMethodExit 中的扩展逻辑
    """
    if span and span.is_recording():
        span.set_attribute("custom.hook.type", "response")
        span.set_attribute("custom.cache.hit", response is not None)
        print(f"  [response_hook] 触发，response={response}")


# =============================================================================
# 第三部分：全局埋点演示
# =============================================================================

print_header("第三部分：全局埋点演示")

print_section("3.1 执行全局埋点")

# 【与 Java 对比】
# Java Agent: 自动在类加载时应用字节码增强
# Python: 需要显式调用 instrument() 方法

MyCacheInstrumentor().instrument(
    request_hook=my_request_hook,
    response_hook=my_response_hook,
)
print("✓ MyCacheInstrumentor.instrument() 已调用")
print("  - 已包装 mycache.CacheClient.get/set/delete 方法")
print("  - 之后创建的所有 CacheClient 实例都会自动埋点")

print_section("3.2 创建客户端并执行操作")

# 创建客户端（在 instrument() 之后）
client = mycache.CacheClient(host="cache.example.com", port=11211, db=1)

print("\n[操作] client.set('user:1001', {'name': 'Alice'})")
print("-" * 60)
client.set("user:1001", {"name": "Alice"})

print("\n[操作] client.get('user:1001')")
print("-" * 60)
result = client.get("user:1001")
print(f"[结果] {result}")

print("\n[操作] client.get('user:9999') - 缓存未命中")
print("-" * 60)
result = client.get("user:9999")
print(f"[结果] {result}")


# =============================================================================
# 第四部分：抑制埋点演示
# =============================================================================

print_header("第四部分：抑制埋点（suppress_instrumentation）")

from opentelemetry.instrumentation.utils import suppress_instrumentation

print("""
【说明】
在某些场景下，我们不希望创建 Span（如内部健康检查、初始化操作）
使用 suppress_instrumentation 上下文管理器可以临时禁用埋点

【与 Java 对比】
Java 中类似的机制：
- AgentSpan.noopIfNoSpan()
- TracingContextUtils.currentContextWith(NoopSpan)
""")

print("\n[操作] 正常调用 - 会创建 Span")
print("-" * 60)
client.get("normal-key")

print("\n[操作] 在 suppress_instrumentation 中调用 - 不会创建 Span")
print("-" * 60)
with suppress_instrumentation():
    client.get("internal-health-check")
    client.set("internal-flag", True)
print("✓ 以上操作没有创建 Span")

print("\n[操作] 退出 suppress 后恢复正常")
print("-" * 60)
client.get("after-suppress")


# =============================================================================
# 第五部分：卸载埋点演示
# =============================================================================

print_header("第五部分：卸载埋点（uninstrument）")

print("""
【与 Java 对比】
Java Agent 通常不支持运行时卸载，因为字节码已被永久修改
Python 可以轻松卸载，因为只是替换了函数引用

【原理】
wrapt 库在包装时保存了原始函数的引用
uninstrument() 调用 unwrap() 恢复原始引用
""")

print("\n[操作] 卸载埋点")
MyCacheInstrumentor().uninstrument()
print("✓ MyCacheInstrumentor.uninstrument() 已调用")

print("\n[操作] 卸载后调用 - 不会创建 Span")
print("-" * 60)
client.get("after-uninstrument")
print("✓ 以上操作没有创建 Span（方法已恢复原始实现）")


# =============================================================================
# 第六部分：单实例埋点演示
# =============================================================================

print_header("第六部分：单实例埋点（instrument_client）")

print("""
【说明】
有时我们只想埋点特定的客户端实例，而不是全局埋点

【使用场景】
- 多个客户端连接不同的缓存集群，只想监控生产环境的
- 某些客户端用于内部操作，不需要监控

【与 Java 对比】
Java Agent 默认全局生效，通常不支持实例级别的控制
Python 的灵活性允许这种细粒度的控制
""")

# 重新导入以获取未被全局包装的类
import importlib
importlib.reload(mycache)

# 创建两个客户端
client_prod = mycache.CacheClient(host="prod-cache.example.com", port=11211)
client_internal = mycache.CacheClient(host="internal-cache.local", port=11211)

# 只对生产环境客户端埋点
print("\n[操作] 只对 client_prod 进行埋点")
MyCacheInstrumentor.instrument_client(
    client_prod,
    request_hook=my_request_hook,
    response_hook=my_response_hook,
)
print("✓ 只有 client_prod 被埋点")

print("\n[操作] client_prod.get('key') - 会创建 Span")
print("-" * 60)
client_prod.get("prod-key")

print("\n[操作] client_internal.get('key') - 不会创建 Span")
print("-" * 60)
client_internal.get("internal-key")
print("✓ 以上操作没有创建 Span")


# =============================================================================
# 总结
# =============================================================================

print_header("总结：Python vs Java Instrumentation 对比")

print("""
+------------------+----------------------------------------+----------------------------------------+
| 特性             | Java (Agent)                           | Python                                 |
+------------------+----------------------------------------+----------------------------------------+
| 埋点时机         | 类加载时（字节码增强）                 | 运行时（函数引用替换）                 |
+------------------+----------------------------------------+----------------------------------------+
| 插件发现         | SPI (META-INF/services)                | Entry Points (pyproject.toml)          |
+------------------+----------------------------------------+----------------------------------------+
| 依赖检测         | 类加载器检测类是否存在                 | packaging 库检测包版本                 |
+------------------+----------------------------------------+----------------------------------------+
| 方法拦截         | ByteBuddy + Advice                     | wrapt.wrap_function_wrapper            |
+------------------+----------------------------------------+----------------------------------------+
| Span 创建        | Tracer.spanBuilder().startSpan()       | tracer.start_as_current_span()         |
+------------------+----------------------------------------+----------------------------------------+
| 上下文管理       | try-finally + Scope                    | with 语句（自动处理）                  |
+------------------+----------------------------------------+----------------------------------------+
| 卸载支持         | 通常不支持                             | 支持（unwrap 恢复原始函数）            |
+------------------+----------------------------------------+----------------------------------------+
| 实例级控制       | 复杂（需要额外逻辑）                   | 简单（instrument_client）              |
+------------------+----------------------------------------+----------------------------------------+
| 异步支持         | CompletableFuture 回调                 | async/await 原生支持                   |
+------------------+----------------------------------------+----------------------------------------+

【核心理解】
1. Python 的 Monkey Patching 本质是替换函数引用，而非修改代码
2. wrapt 库提供了优雅的包装机制，保存原始函数引用
3. Entry Points 机制类似 Java SPI，用于插件发现
4. 依赖检测使用 packaging 库，而非类加载器检测
5. Python 的灵活性允许更细粒度的控制（如实例级埋点）
""")

print("\n✓ 演示完成！")
