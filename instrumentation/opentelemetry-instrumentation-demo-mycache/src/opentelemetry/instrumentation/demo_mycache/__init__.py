# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
==============================================================================
OpenTelemetry Demo MyCache Instrumentation - 教学用例
==============================================================================

本示例展示如何编写一个完整的 Python OT Instrumentation，并与 Java 进行对比。

【目录】
1. 基本概念与架构对比
2. 插件发现机制
3. 依赖检测机制
4. Monkey Patching vs ByteBuddy
5. Span 创建与属性设置
6. Hook 机制
7. 卸载机制

==============================================================================
1. 基本概念与架构对比
==============================================================================

+------------------+--------------------------------+--------------------------------+
| 概念             | Java                           | Python                         |
+------------------+--------------------------------+--------------------------------+
| 插件类           | InstrumentationModule          | BaseInstrumentor               |
| 类型匹配         | TypeInstrumentation            | N/A (直接指定模块.类.方法)     |
| 方法拦截         | ByteBuddy + Advice             | wrapt.wrap_function_wrapper    |
| Span 创建        | Tracer.spanBuilder()           | tracer.start_as_current_span() |
| 上下文传播       | Context.current()              | trace.get_current_span()       |
+------------------+--------------------------------+--------------------------------+

==============================================================================
1.1 【重要】Python OT 插件的两种埋点机制
==============================================================================

Python OT 插件有两种主要的埋点机制，需要根据目标库的特性选择：

┌─────────────────────────────────────────────────────────────────────────────┐
│                     机制一：Monkey Patching（函数包装）                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 代表：Redis、MySQL、Requests、gRPC 等客户端库                                │
│                                                                             │
│ 实现方式：                                                                   │
│   - 使用 wrapt.wrap_function_wrapper() 替换原始方法                         │
│   - 在包装函数中使用 tracer.start_as_current_span() 创建 Span               │
│                                                                             │
│ 适用场景：                                                                   │
│   - 客户端库（CLIENT span）                                                 │
│   - 没有提供原生扩展点的库                                                   │
│   - 需要拦截特定方法调用                                                     │
│                                                                             │
│ 代码示例（Redis）：                                                          │
│   wrapt.wrap_function_wrapper(                                              │
│       "redis", "Redis.execute_command", _traced_execute_command             │
│   )                                                                         │
│                                                                             │
│   def _traced_execute_command(wrapped, instance, args, kwargs):             │
│       with tracer.start_as_current_span("redis.command") as span:           │
│           return wrapped(*args, **kwargs)                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    机制二：框架原生扩展点（中间件/拦截器）                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 代表：Django、Flask、FastAPI、Tornado 等 Web 框架                           │
│                                                                             │
│ 实现方式：                                                                   │
│   - 利用框架提供的 Middleware（中间件）机制                                  │
│   - 在 _instrument() 中将 OT 中间件注入到框架的中间件列表                   │
│   - 使用 use_span() + activation.__enter__() 手动管理 Span 生命周期         │
│                                                                             │
│ 适用场景：                                                                   │
│   - Web 框架（SERVER span）                                                 │
│   - 框架本身提供了扩展机制                                                   │
│   - 需要访问框架特有的上下文（如 request、response）                         │
│                                                                             │
│ 为什么 Django 不用 wrap_function_wrapper？                                  │
│   1. Django 已有完善的 Middleware 机制，符合框架设计理念                    │
│   2. 中间件能自然获取 request/response 生命周期                             │
│   3. 避免 Monkey Patching 可能带来的兼容性问题                              │
│   4. 更好地控制执行顺序（中间件顺序可配置）                                  │
└─────────────────────────────────────────────────────────────────────────────┘

【Django 中间件机制详解】

Django 埋点的核心是 _DjangoMiddleware 类，它继承自 MiddlewareMixin：

┌─────────────────────────────────────────────────────────────────────────────┐
│                          Django 请求处理流程                                 │
│                                                                             │
│  HTTP 请求                                                                  │
│      │                                                                      │
│      ▼                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ _DjangoMiddleware.process_request(request)                       │      │
│  │   │                                                              │      │
│  │   │ 1. 收集请求属性 (URL、method、headers 等)                    │      │
│  │   │ 2. 调用 _start_internal_or_server_span() 创建 SERVER span    │      │
│  │   │ 3. activation = use_span(span, end_on_exit=True)            │      │
│  │   │ 4. activation.__enter__()  ← 激活 Span，设置为当前上下文     │      │
│  │   │ 5. 将 activation 和 span 存入 request.META                   │      │
│  │   ▼                                                              │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│      │                                                                      │
│      ▼                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ 其他中间件 + View 函数执行                                        │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│      │                                                                      │
│      ▼                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │ _DjangoMiddleware.process_response(request, response)            │      │
│  │   │                                                              │      │
│  │   │ 1. 从 request.META 取出 activation 和 span                   │      │
│  │   │ 2. 设置 response 状态码等属性                                │      │
│  │   │ 3. activation.__exit__()  ← 结束 Span，发送到后端            │      │
│  │   ▼                                                              │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│      │                                                                      │
│      ▼                                                                      │
│  HTTP 响应                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘

【Django 关键代码分析】

# 在 DjangoInstrumentor._instrument() 中：
# 不是用 wrap_function_wrapper，而是将中间件类注入到 settings.MIDDLEWARE
settings_middleware.insert(middleware_position, self._opentelemetry_middleware)
setattr(settings, _middleware_setting, settings_middleware)

# 在 _DjangoMiddleware.process_request() 中：
# 不用 start_as_current_span()，而是用 _start_internal_or_server_span() + use_span()
span, token = _start_internal_or_server_span(
    tracer=self._tracer,
    span_name=self._get_span_name(request),
    context_carrier=carrier,
    context_getter=carrier_getter,
    attributes=attributes,
)

# 手动管理 Span 生命周期
activation = use_span(span, end_on_exit=True)
activation.__enter__()  # 进入上下文，激活 Span
# ... 存储到 request.META 供 process_response 使用

# 在 process_response() 中：
activation.__exit__(None, None, None)  # 退出上下文，结束 Span

【为什么要用 use_span() 而不是 start_as_current_span()？】

start_as_current_span() 是 with 语句使用的：
    with tracer.start_as_current_span("op"):  # 同一个方法内开始和结束
        do_something()

但 Django 中间件的特点是：
    - process_request() 中开始 Span
    - process_response() 中结束 Span  ← 不同的方法！

所以需要用更底层的 API：
    - use_span() 返回一个 context manager（activation）
    - 手动调用 __enter__() 和 __exit__() 控制生命周期
    - 通过 request.META 在不同方法间传递 activation 对象

【与 Java 的对比】

┌─────────────────────────────────────────────────────────────────────────────┐
│                     Java Web 框架埋点方式对比                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ Java Servlet（字节码增强）:                                                 │
│   - 使用 ByteBuddy 拦截 Servlet.service() 方法                              │
│   - 在 @OnMethodEnter 创建 Span，@OnMethodExit 结束 Span                    │
│                                                                             │
│ Java Spring（混合方式）:                                                    │
│   - 可以用 HandlerInterceptor（类似 Django Middleware）                     │
│   - 也可以用字节码增强拦截 Controller 方法                                  │
│                                                                             │
│ Python Django（框架扩展点）:                                                │
│   - 完全使用 Django 原生的 Middleware 机制                                  │
│   - 不做任何 Monkey Patching                                                │
│   - 符合 Django 的设计理念，兼容性最好                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

【总结：如何选择埋点机制？】

判断标准：目标库是否提供扩展点？

    ┌─────────────────────┐
    │ 目标库有扩展点吗？   │
    └──────────┬──────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
      YES             NO
       │               │
       ▼               ▼
   使用框架扩展点    使用 Monkey Patching
   (如 Middleware)   (wrap_function_wrapper)
       │               │
       ▼               ▼
   Django、Flask    Redis、MySQL、
   FastAPI 等       Requests 等

==============================================================================
2. 使用方式
==============================================================================

方式一：全局自动埋点（类似 Java Agent 方式）
-----------------------------------------
# 使用 opentelemetry-instrument 命令启动
$ opentelemetry-instrument python app.py

# 框架会自动：
# 1. 扫描所有 opentelemetry_instrumentor entry points
# 2. 检查 instruments 依赖是否满足
# 3. 调用 instrument() 方法

方式二：手动埋点
-----------------------------------------
from opentelemetry.instrumentation.demo_mycache import MyCacheInstrumentor

# 手动初始化
MyCacheInstrumentor().instrument()

# 之后创建的所有 CacheClient 实例都会被自动埋点
client = mycache.CacheClient()
client.get("key")  # 这里会自动创建 Span

方式三：只埋点特定实例
-----------------------------------------
from opentelemetry.instrumentation.demo_mycache import MyCacheInstrumentor

# 不调用全局 instrument()
client1 = mycache.CacheClient()  # 不会被埋点
client2 = mycache.CacheClient()

# 只埋点 client2
MyCacheInstrumentor.instrument_client(client2)

client1.get("key")  # 无 Span
client2.get("key")  # 有 Span

==============================================================================
3. Hook 机制
==============================================================================

def request_hook(span, instance, args, kwargs):
    '''请求前回调，可添加自定义属性'''
    if span and span.is_recording():
        span.set_attribute("custom.key", args[0])

def response_hook(span, instance, response):
    '''响应后回调，可记录返回值相关信息'''
    if span and span.is_recording():
        span.set_attribute("cache.hit", response is not None)

MyCacheInstrumentor().instrument(
    request_hook=request_hook,
    response_hook=response_hook
)

【与 Java 对比】
Java 中通常使用 Advice 的 @OnMethodEnter 和 @OnMethodExit 来实现类似功能

API
---
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Collection

# wrapt 是 Python 中实现 Monkey Patching 的标准库
# 【与 Java 对比】Java 使用 ByteBuddy 进行字节码增强
from wrapt import wrap_function_wrapper

from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.demo_mycache.package import _instruments
from opentelemetry.instrumentation.demo_mycache.version import __version__
from opentelemetry.instrumentation.utils import (
    is_instrumentation_enabled,  # 检查是否在 suppress_instrumentation 上下文中
    unwrap,  # 用于卸载时恢复原始方法
)
from opentelemetry.semconv._incubating.attributes.db_attributes import (
    DB_STATEMENT,
    DB_SYSTEM,
)
from opentelemetry.trace import (
    SpanKind,
    StatusCode,
    Tracer,
    TracerProvider,
    get_tracer,
)

# =============================================================================
# 问题1：if TYPE_CHECKING 是干什么的？
# =============================================================================
# 【解答】
# TYPE_CHECKING 是一个特殊的常量，它的值：
#   - 在运行时（runtime）：值为 False，if 块里的代码不会执行
#   - 在类型检查时（如 IDE 检查、mypy 检查）：值为 True，if 块里的代码会被分析
#
# 【为什么要这样做？】
# 1. 避免循环导入：有些类型定义可能导致循环导入问题
# 2. 减少运行时开销：类型注解只在开发/检查时有用，运行时不需要
# 3. 可选依赖：typing 模块的某些类型在运行时不需要
#
# 【与 Java 对比】
# Java 没有这个概念，因为 Java 的类型信息在编译时就确定了
# Python 是动态类型语言，类型注解是"可选的提示"，不影响运行
#
# =============================================================================
# 问题2：类型注解是干什么的，有什么用？
# =============================================================================
# 【解答】
# 类型注解（Type Hints）是 Python 3.5+ 引入的特性，用于标注变量、参数、返回值的类型
#
# 【作用】
# 1. IDE 智能提示：让编辑器知道变量是什么类型，提供更好的代码补全
# 2. 静态类型检查：使用 mypy 等工具在运行前发现类型错误
# 3. 代码文档：让其他开发者一眼看懂函数参数和返回值
# 4. 不影响运行：类型注解只是"提示"，Python 运行时不会强制检查
#
# 【与 Java 对比】
# Java: public String getName(int id) { ... }  // 类型是强制的
# Python: def get_name(id: int) -> str: ...    // 类型是可选的提示
#
# 【示例】
# def add(a: int, b: int) -> int:
#     return a + b
# add("1", "2")  # 运行时不报错，但 IDE/mypy 会警告类型不匹配
#
# =============================================================================
# 问题3：Hook 是干什么的？
# =============================================================================
# 【解答】
# Hook（钩子）是一种扩展机制，允许用户在特定时机插入自定义逻辑
#
# 【这里定义的两种 Hook】
# 1. RequestHook：在执行目标方法之前调用，可以添加自定义属性
# 2. ResponseHook：在执行目标方法之后调用，可以记录响应信息
#
# 【使用场景】
# - 添加业务相关的自定义属性（如用户ID、订单号）
# - 记录缓存命中率
# - 记录响应大小
#
# 【与 Java 对比】
# Java 中类似的机制：
# - Advice 的 @OnMethodEnter / @OnMethodExit
# - 拦截器（Interceptor）的 preHandle / postHandle
#
# 【使用示例】
# def my_request_hook(span, instance, args, kwargs):
#     span.set_attribute("my.custom.key", args[0])
#
# def my_response_hook(span, instance, response):
#     span.set_attribute("cache.hit", response is not None)
#
# MyCacheInstrumentor().instrument(
#     request_hook=my_request_hook,
#     response_hook=my_response_hook
# )
# =============================================================================

if TYPE_CHECKING:
    # 【这部分代码只在类型检查时执行，运行时不执行】
    
    from typing import TypeVar
    R = TypeVar("R")  # 泛型类型变量，表示"任意返回值类型"
    
    # 【Hook 函数的类型定义】
    # RequestHook: 接收 (span, instance, args, kwargs) 四个参数，无返回值
    #   - span: 当前 Span 对象，可以设置属性
    #   - instance: 客户端实例（self）
    #   - args: 位置参数元组，如 client.get("key") 的 args = ("key",)
    #   - kwargs: 关键字参数字典
    RequestHook = Callable[[trace.Span, Any, tuple, dict], None]
    
    # ResponseHook: 接收 (span, instance, response) 三个参数，无返回值
    #   - span: 当前 Span 对象
    #   - instance: 客户端实例
    #   - response: 方法的返回值
    ResponseHook = Callable[[trace.Span, Any, Any], None]


_logger = logging.getLogger(__name__)

# 用于标记实例是否已被埋点，避免重复埋点
_INSTRUMENTATION_ATTR = "_is_instrumented_by_opentelemetry"


# =============================================================================
# 工厂函数：创建包装后的方法
# =============================================================================
# 【与 Java 对比】
# 
# Java Advice 写法：
# ```java
# @Advice.OnMethodEnter(suppress = Throwable.class)
# public static void onEnter(
#     @Advice.Argument(0) String key,
#     @Advice.Local("otelSpan") Span span,
#     @Advice.Local("otelScope") Scope scope) {
#     
#     span = tracer.spanBuilder("cache.get")
#         .setSpanKind(SpanKind.CLIENT)
#         .setAttribute("db.operation", "get")
#         .startSpan();
#     scope = span.makeCurrent();
# }
#
# @Advice.OnMethodExit(onThrowable = Throwable.class, suppress = Throwable.class)
# public static void onExit(
#     @Advice.Return Object result,
#     @Advice.Thrown Throwable throwable,
#     @Advice.Local("otelSpan") Span span,
#     @Advice.Local("otelScope") Scope scope) {
#     
#     if (throwable != null) {
#         span.setStatus(StatusCode.ERROR, throwable.getMessage());
#     }
#     scope.close();
#     span.end();
# }
# ```
#
# Python 使用函数包装器实现相同功能：

def _traced_execute_factory(
    tracer: Tracer,
    request_hook: RequestHook | None = None,
    response_hook: ResponseHook | None = None,
):
    """
    工厂函数：创建一个包装函数，用于拦截目标方法调用
    
    【设计模式】工厂模式
    为什么使用工厂函数？
    1. 需要在包装函数中使用 tracer 和 hooks，但 wrap_function_wrapper 不支持传参
    2. 通过闭包捕获这些变量
    
    【与 Java 对比】
    Java 使用 Advice 类的静态方法，通过 @Advice.Local 传递状态
    Python 使用闭包捕获状态
    """
    
    def _traced_execute_command(
        func: Callable[..., R],      # 原始方法（被包装的方法）
        instance: Any,                # 实例对象（self）
        args: tuple[Any, ...],        # 位置参数
        kwargs: dict[str, Any],       # 关键字参数
    ) -> R:
        """
        实际的包装函数，在原始方法前后添加埋点逻辑
        
        【参数说明】（wrapt 的标准签名）
        - func: 原始方法的引用
        - instance: 调用方法的实例（相当于 Java 的 this）
        - args: 位置参数元组，如 client.get("key") -> args = ("key",)
        - kwargs: 关键字参数字典
        
        【与 Java 对比】
        Java 通过 @Advice.Argument(N) 获取参数
        Python 直接通过 args 和 kwargs 访问
        """
        
        # ---------------------------------------------------------------------
        # Step 1: 检查是否启用埋点
        # ---------------------------------------------------------------------
        # suppress_instrumentation 上下文管理器可以临时禁用埋点
        # 用途：避免在内部操作（如健康检查）中创建 Span
        #
        # 使用示例：
        # with suppress_instrumentation():
        #     client.get("internal-key")  # 不会创建 Span
        #
        # 【与 Java 对比】
        # Java 中类似的机制是 AgentSpan.noopIfNoSpan() 或检查 suppressionStrategy
        if not is_instrumentation_enabled():
            return func(*args, **kwargs)
        
        # ---------------------------------------------------------------------
        # Step 2: 构建 Span 名称和属性
        # ---------------------------------------------------------------------
        # 从参数中提取操作名称
        operation = args[0] if args else "unknown"
        span_name = f"mycache.{operation}"
        
        # 构建语句描述（类似 SQL 语句）
        # 格式化为 "GET key" 或 "SET key value"
        statement = _format_command(args)
        
        # ---------------------------------------------------------------------
        # Step 3: 创建并管理 Span
        # ---------------------------------------------------------------------
        # 【与 Java 对比】
        # 
        # Java:
        #   Span span = tracer.spanBuilder("mycache.get")
        #       .setSpanKind(SpanKind.CLIENT)
        #       .startSpan();
        #   try (Scope scope = span.makeCurrent()) {
        #       // 执行原始方法
        #   } finally {
        #       span.end();
        #   }
        #
        # Python 使用上下文管理器自动处理 span.end() 和 scope 管理：
        with tracer.start_as_current_span(
            span_name,
            kind=SpanKind.CLIENT  # CLIENT 类型，表示这是客户端调用外部服务
        ) as span:
            
            # -----------------------------------------------------------------
            # Step 4: 设置 Span 属性
            # -----------------------------------------------------------------
            if span.is_recording():
                # 设置标准语义属性
                # 【语义约定】参考 https://opentelemetry.io/docs/specs/semconv/
                span.set_attribute(DB_SYSTEM, "mycache")  # db.system
                span.set_attribute(DB_STATEMENT, statement)  # db.statement
                span.set_attribute("db.operation", operation)
                
                # 设置连接属性
                _set_connection_attributes(span, instance)
                
                # 设置自定义属性
                span.set_attribute("mycache.args_length", len(args))
            
            # -----------------------------------------------------------------
            # Step 5: 调用 request_hook（请求前回调）
            # -----------------------------------------------------------------
            # 【用途】用户可以在此添加自定义属性
            # 【与 Java 对比】类似 Advice.OnMethodEnter 的扩展点
            if callable(request_hook):
                request_hook(span, instance, args, kwargs)
            
            # -----------------------------------------------------------------
            # Step 6: 执行原始方法
            # -----------------------------------------------------------------
            try:
                response = func(*args, **kwargs)
            except Exception as exc:
                # 记录异常信息
                # 【与 Java 对比】类似 @Advice.Thrown
                if span.is_recording():
                    span.set_status(StatusCode.ERROR, str(exc))
                    span.record_exception(exc)
                raise
            
            # -----------------------------------------------------------------
            # Step 7: 调用 response_hook（响应后回调）
            # -----------------------------------------------------------------
            # 【与 Java 对比】类似 Advice.OnMethodExit
            if callable(response_hook):
                response_hook(span, instance, response)
            
            return response
    
    return _traced_execute_command


def _traced_async_execute_factory(
    tracer: Tracer,
    request_hook: RequestHook | None = None,
    response_hook: ResponseHook | None = None,
):
    """
    异步方法的包装工厂
    
    【与 Java 对比】
    Java 中处理异步通常需要特殊的 Advice 或使用 CompletableFuture 回调
    Python 中只需将函数改为 async/await
    
    ==========================================================================
    【Java 异步埋点示例 - 使用 CompletableFuture】
    ==========================================================================
    
    // Java 中对异步方法的埋点比较复杂，需要处理回调链
    public class AsyncRedisAdvice {
        
        @Advice.OnMethodEnter
        public static void onEnter(
            @Advice.Local("span") Span span,
            @Advice.Local("scope") Scope scope
        ) {
            // 1. 创建 Span
            span = tracer.spanBuilder("redis.GET").startSpan();
            // 2. 激活 Scope（让 Span 成为当前上下文）
            scope = span.makeCurrent();
        }
        
        @Advice.OnMethodExit
        public static void onExit(
            @Advice.Return CompletableFuture<?> future,  // 返回的是 Future
            @Advice.Local("span") Span span,
            @Advice.Local("scope") Scope scope
        ) {
            // 3. 必须先关闭 Scope（但不能关闭 Span！）
            scope.close();
            
            // ================================================================
            // 【重要概念】Scope 和 Span 的关闭差异
            // ================================================================
            //
            // ┌─────────────────────────────────────────────────────────────────┐
            // │                      概念对比图                                  │
            // ├─────────────────────────────────────────────────────────────────┤
            // │                                                                 │
            // │   Span（跨度）                    Scope（作用域）                │
            // │   ┌─────────────────┐            ┌─────────────────┐           │
            // │   │ 代表一个操作    │            │ 代表 Span 的    │           │
            // │   │ 的时间段记录    │            │ "当前激活状态"  │           │
            // │   │                 │            │                 │           │
            // │   │ 包含:           │            │ 作用:           │           │
            // │   │ - 开始/结束时间 │            │ - 将 Span 绑定  │           │
            // │   │ - 属性          │            │   到当前线程    │           │
            // │   │ - 事件          │            │ - 子 Span 能    │           │
            // │   │ - 状态          │            │   找到父 Span   │           │
            // │   └─────────────────┘            └─────────────────┘           │
            // │                                                                 │
            // │   生命周期:                      生命周期:                      │
            // │   span.end() 时结束              scope.close() 时结束          │
            // │   (记录完成，发送数据)           (解除线程绑定)                 │
            // │                                                                 │
            // └─────────────────────────────────────────────────────────────────┘
            //
            // 【类比理解】
            // ┌─────────────────────────────────────────────────────────────────┐
            // │ Span  = 一本正在写的日记本（记录操作内容）                       │
            // │ Scope = 把日记本放在桌上（让当前线程可以访问它）                 │
            // │                                                                 │
            // │ scope.close() = 把日记本从桌上拿走（但日记本还没写完）           │
            // │ span.end()    = 合上日记本，写作完成（内容固定，准备归档）       │
            // └─────────────────────────────────────────────────────────────────┘
            //
            // 【为什么异步场景必须分开关闭？】
            //
            // 同步场景（简单）:
            // ┌──────────────────────────────────────────────────────────────────┐
            // │ Thread-1: ──[Scope开始]──[操作执行]──[Scope关闭+Span结束]──      │
            // │                   ↑                        ↑                     │
            // │               同一线程，可以一起关闭                              │
            // └──────────────────────────────────────────────────────────────────┘
            //
            // 异步场景（复杂）:
            // ┌──────────────────────────────────────────────────────────────────┐
            // │ Thread-1: ──[Scope开始]──[发起异步调用]──[Scope必须关闭]──→继续   │
            // │                               │              ↑                   │
            // │                               │      线程要去干别的事了，         │
            // │                               │      必须解除 Span 绑定          │
            // │                               ↓                                  │
            // │ Thread-2: ─────────────[异步回调执行]──[Span结束]──               │
            // │                               ↑              ↑                   │
            // │                        操作真正完成，      这时才能结束 Span       │
            // │                        可能在另一个线程                           │
            // └──────────────────────────────────────────────────────────────────┘
            //
            // 【Java 代码示例】
            //
            // 错误写法（会导致内存泄漏或数据不准确）:
            // void wrongWay() {
            //     Span span = tracer.spanBuilder("op").startSpan();
            //     Scope scope = span.makeCurrent();
            //     asyncOperation().whenComplete((r, e) -> {
            //         span.end();  // ❌ Scope 没关闭，线程本地变量泄漏！
            //     });
            //     // ❌ 方法结束，scope 没有显式关闭
            // }
            //
            // 正确写法:
            // void correctWay() {
            //     Span span = tracer.spanBuilder("op").startSpan();
            //     Scope scope = span.makeCurrent();
            //     try {
            //         asyncOperation().whenComplete((r, e) -> {
            //             span.end();  // ✅ 异步完成时结束 Span
            //         });
            //     } finally {
            //         scope.close();  // ✅ 同步方法返回前关闭 Scope
            //     }
            // }
            //
            // 【Python 为什么不需要这么复杂？】
            //
            // Python 的 async/await 是"协程"模型，不是真正的多线程：
            // - 协程在 await 时暂停，恢复时上下文自动恢复
            // - with 语句保证 Span 和 Scope 同时正确管理
            // - 不需要手动处理线程本地变量
            //
            // Python 等价代码:
            // async def python_way():
            //     with tracer.start_as_current_span("op") as span:
            //         # with 同时管理 Scope 和 Span
            //         result = await async_operation()  # 暂停/恢复上下文自动处理
            //     # with 退出时，Scope 和 Span 一起正确关闭
            //
            // ================================================================
            
            // 4. 在 Future 完成时才能关闭 Span
            Context context = Context.current();  // 捕获当前上下文
            future.whenComplete((result, error) -> {
                // 5. 恢复上下文
                try (Scope ignored = context.makeCurrent()) {
                    if (error != null) {
                        span.setStatus(StatusCode.ERROR);
                        span.recordException(error);
                    }
                    // 6. 最后关闭 Span
                    span.end();
                }
            });
        }
    }
    
    ==========================================================================
    【Python 异步埋点示例 - 使用 async/await】
    ==========================================================================
    
    # Python 中异步埋点非常简单，只需添加 async/await 关键字
    async def traced_async_get(original_func, instance, args, kwargs):
        with tracer.start_as_current_span("redis.GET") as span:
            try:
                # 只需 await 原始方法，上下文自动传递！
                result = await original_func(*args, **kwargs)
                return result
            except Exception as e:
                span.set_status(StatusCode.ERROR)
                span.record_exception(e)
                raise
    
    # 对比关键点：
    # ┌─────────────────┬──────────────────────────────────────────────────────┐
    # │     方面        │   Java                        │   Python             │
    # ├─────────────────┼──────────────────────────────────────────────────────┤
    # │ 上下文管理      │ 手动管理 Scope.close()        │ with 语句自动管理    │
    # │ Span 生命周期   │ 必须在回调中 span.end()       │ with 语句自动结束    │
    # │ 异步等待        │ CompletableFuture.whenComplete│ await 关键字         │
    # │ 上下文传递      │ 需要手动捕获和恢复 Context    │ 自动传递（协程特性） │
    # │ 代码复杂度      │ 高（回调地狱风险）            │ 低（同步风格写法）   │
    # └─────────────────┴──────────────────────────────────────────────────────┘
    """
    
    async def _traced_async_execute_command(
        func: Callable[..., Any],
        instance: Any,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        if not is_instrumentation_enabled():
            return await func(*args, **kwargs)
        
        operation = args[0] if args else "unknown"
        span_name = f"mycache.{operation}"
        statement = _format_command(args)
        
        with tracer.start_as_current_span(
            span_name,
            kind=SpanKind.CLIENT
        ) as span:
            if span.is_recording():
                span.set_attribute(DB_SYSTEM, "mycache")
                span.set_attribute(DB_STATEMENT, statement)
                span.set_attribute("db.operation", operation)
                _set_connection_attributes(span, instance)
            
            if callable(request_hook):
                request_hook(span, instance, args, kwargs)
            
            try:
                # 注意这里使用 await
                response = await func(*args, **kwargs)
            except Exception as exc:
                if span.is_recording():
                    span.set_status(StatusCode.ERROR, str(exc))
                    span.record_exception(exc)
                raise
            
            if callable(response_hook):
                response_hook(span, instance, response)
            
            return response
    
    return _traced_async_execute_command


# =============================================================================
# 辅助函数
# =============================================================================

def _format_command(args: tuple) -> str:
    """
    格式化命令参数为可读字符串
    
    【安全考虑】
    不记录实际的 value，只记录 key 名称，避免敏感数据泄露
    
    示例：
    - args = ("get", "user:123") -> "GET user:123"
    - args = ("set", "user:123", "secret") -> "SET user:123 ?"
    """
    if not args:
        return ""
    
    operation = str(args[0]).upper()
    if len(args) > 1:
        key = str(args[1])
        if len(args) > 2:
            # 隐藏 value，用 ? 代替
            return f"{operation} {key} ?"
        return f"{operation} {key}"
    return operation


def _set_connection_attributes(span: trace.Span, instance: Any) -> None:
    """
    从实例中提取连接属性并设置到 Span
    
    【语义约定属性】
    - net.peer.name: 服务器主机名
    - net.peer.port: 服务器端口
    - db.name: 数据库名称
    """
    if not span.is_recording():
        return
    
    # 尝试从实例中获取连接信息
    # 实际实现需要根据目标库的 API 调整
    if hasattr(instance, "host"):
        span.set_attribute("net.peer.name", instance.host)
    if hasattr(instance, "port"):
        span.set_attribute("net.peer.port", instance.port)
    if hasattr(instance, "db"):
        span.set_attribute("db.name", str(instance.db))


# =============================================================================
# 全局埋点函数
# =============================================================================

def _instrument(
    tracer: Tracer,
    request_hook: RequestHook | None = None,
    response_hook: ResponseHook | None = None,
):
    """
    执行全局埋点，包装目标库的所有相关方法
    
    【与 Java 对比】
    
    Java 使用 TypeTransformer 和 ByteBuddy：
    ```java
    @Override
    public void transform(TypeTransformer transformer) {
        transformer.applyAdviceToMethod(
            named("execute"),  // 匹配方法名
            this.getClass().getName() + "$ExecuteAdvice"
        );
    }
    ```
    
    Python 使用 wrapt.wrap_function_wrapper：
    - 第一个参数：模块名
    - 第二个参数：类名.方法名
    - 第三个参数：包装函数
    """
    
    # 创建包装函数
    _traced_execute = _traced_execute_factory(tracer, request_hook, response_hook)
    _traced_async_execute = _traced_async_execute_factory(tracer, request_hook, response_hook)
    
    # -------------------------------------------------------------------------
    # 包装同步客户端方法
    # -------------------------------------------------------------------------
    # 【与 Java 对比】
    # Java: transformer.applyAdviceToMethod(named("get"), GetAdvice.class.getName())
    # Python: wrap_function_wrapper("模块", "类.方法", 包装函数)
    
    wrap_function_wrapper(
        "mycache",           # 模块名（相当于 Java 的包名）
        "CacheClient.get",   # 类名.方法名
        _traced_execute      # 包装函数
    )
    
    wrap_function_wrapper(
        "mycache",
        "CacheClient.set",
        _traced_execute
    )
    
    wrap_function_wrapper(
        "mycache",
        "CacheClient.delete",
        _traced_execute
    )
    
    # -------------------------------------------------------------------------
    # 包装异步客户端方法
    # -------------------------------------------------------------------------
    wrap_function_wrapper(
        "mycache.asyncio",
        "AsyncCacheClient.get",
        _traced_async_execute
    )
    
    wrap_function_wrapper(
        "mycache.asyncio",
        "AsyncCacheClient.set",
        _traced_async_execute
    )
    
    _logger.debug("MyCacheInstrumentor: 全局埋点完成")


def _instrument_client(
    client: Any,
    tracer: Tracer,
    request_hook: RequestHook | None = None,
    response_hook: ResponseHook | None = None,
):
    """
    只对单个客户端实例进行埋点
    
    【使用场景】
    - 有多个客户端实例，只想埋点特定的
    - 不同客户端需要不同的 hook 配置
    
    【与 Java 对比】
    Java Agent 默认全局生效，没有对单个实例埋点的原生支持
    Python 可以灵活地只对特定实例进行包装
    """
    
    _traced_execute = _traced_execute_factory(tracer, request_hook, response_hook)
    
    # 对实例的方法进行包装
    wrap_function_wrapper(client, "get", _traced_execute)
    wrap_function_wrapper(client, "set", _traced_execute)
    wrap_function_wrapper(client, "delete", _traced_execute)


# =============================================================================
# MyCacheInstrumentor 类 - 插件主类
# =============================================================================
# 
# 【与 Java 对比】
#
# Java InstrumentationModule:
# ```java
# @AutoService(InstrumentationModule.class)
# public class MyCacheInstrumentationModule extends InstrumentationModule {
#     
#     public MyCacheInstrumentationModule() {
#         super("mycache", "mycache-1.0");
#     }
#     
#     @Override
#     public List<TypeInstrumentation> typeInstrumentations() {
#         return singletonList(new CacheClientInstrumentation());
#     }
#     
#     @Override
#     public ElementMatcher<ClassLoader> classLoaderOptimization() {
#         return hasClassesNamed("com.example.mycache.CacheClient");
#     }
# }
# ```
#
# Python BaseInstrumentor:
# - 继承 BaseInstrumentor
# - 实现 instrumentation_dependencies() 声明依赖
# - 实现 _instrument() 执行埋点
# - 实现 _uninstrument() 卸载埋点

class MyCacheInstrumentor(BaseInstrumentor):
    """
    MyCache 插件主类
    
    【生命周期】
    1. 插件发现：框架扫描 entry_points，找到此类
    2. 依赖检测：调用 instrumentation_dependencies()，检查 mycache 是否已安装
    3. 执行埋点：调用 instrument() -> _instrument()
    4. 运行时：每次调用 mycache 方法时，执行包装函数
    5. 卸载埋点：调用 uninstrument() -> _uninstrument()
    
    【单例模式】
    BaseInstrumentor 实现了单例模式，确保全局只有一个实例
    这与 Java 中 InstrumentationModule 的行为一致
    """
    
    @staticmethod
    def _get_tracer(**kwargs) -> Tracer:
        """
        获取 Tracer 实例
        
        【与 Java 对比】
        Java: GlobalOpenTelemetry.getTracer("instrumentation-name", "version")
        Python: get_tracer(__name__, __version__, tracer_provider=tracer_provider)
        """
        tracer_provider = kwargs.get("tracer_provider")
        return get_tracer(
            __name__,                    # 插件名称
            __version__,                 # 插件版本
            tracer_provider=tracer_provider,
            schema_url="https://opentelemetry.io/schemas/1.11.0",
        )
    
    def instrumentation_dependencies(self) -> Collection[str]:
        """
        返回目标库的依赖声明
        
        【核心方法】此方法决定插件是否生效
        
        【流程】
        1. BaseInstrumentor.instrument() 调用此方法
        2. 框架使用 packaging 库解析依赖字符串 "mycache >= 1.0"
        3. 使用 importlib.metadata.version("mycache") 获取已安装版本
        4. 比较版本是否满足约束
        5. 不满足则返回 DependencyConflict，插件不生效
        
        【与 Java 对比】
        Java:
        ```java
        @Override
        public ElementMatcher<ClassLoader> classLoaderOptimization() {
            return hasClassesNamed("com.example.mycache.CacheClient");
        }
        ```
        
        Java 通过类加载器检测类是否存在
        Python 通过 pip 包版本检测
        """
        return _instruments
    
    def instrument(
        self,
        tracer_provider: TracerProvider | None = None,
        request_hook: RequestHook | None = None,
        response_hook: ResponseHook | None = None,
        **kwargs,
    ):
        """
        公开的埋点入口方法
        
        【参数说明】
        - tracer_provider: 自定义 TracerProvider，默认使用全局
        - request_hook: 请求前回调
        - response_hook: 响应后回调
        
        【调用方式】
        1. 自动埋点：opentelemetry-instrument 命令调用（无参数）
        2. 手动埋点：MyCacheInstrumentor().instrument(tracer_provider=xxx)
        """
        super().instrument(
            tracer_provider=tracer_provider,
            request_hook=request_hook,
            response_hook=response_hook,
            **kwargs,
        )
    
    def _instrument(self, **kwargs: Any):
        """
        实际执行埋点的内部方法
        
        【与 Java 对比】
        Java: TypeInstrumentation.transform() 方法
        Python: _instrument() 方法
        
        【注意】
        - 此方法由 BaseInstrumentor.instrument() 调用
        - 在依赖检测通过后才会调用
        - 只会调用一次（单例模式保证）
        """
        _instrument(
            self._get_tracer(**kwargs),
            request_hook=kwargs.get("request_hook"),
            response_hook=kwargs.get("response_hook"),
        )
    
    def _uninstrument(self, **kwargs: Any):
        """
        卸载埋点，恢复原始方法
        
        【与 Java 对比】
        Java Agent 通常不支持卸载，因为字节码已被修改
        Python 可以轻松卸载，因为只是替换了函数引用
        
        【实现原理】
        wrapt 的 wrap_function_wrapper 会保存原始函数引用
        unwrap 函数会恢复原始引用
        """
        # 导入目标模块
        import mycache
        import mycache.asyncio
        
        # 恢复同步客户端的原始方法
        unwrap(mycache.CacheClient, "get")
        unwrap(mycache.CacheClient, "set")
        unwrap(mycache.CacheClient, "delete")
        
        # 恢复异步客户端的原始方法
        unwrap(mycache.asyncio.AsyncCacheClient, "get")
        unwrap(mycache.asyncio.AsyncCacheClient, "set")
        
        _logger.debug("MyCacheInstrumentor: 埋点已卸载")
    
    @staticmethod
    def instrument_client(
        client: Any,
        tracer_provider: TracerProvider | None = None,
        request_hook: RequestHook | None = None,
        response_hook: ResponseHook | None = None,
    ):
        """
        静态方法：只对单个客户端实例进行埋点
        
        【使用场景】
        不想全局埋点，只对特定实例埋点
        
        【示例】
        client1 = mycache.CacheClient()
        client2 = mycache.CacheClient()
        
        MyCacheInstrumentor.instrument_client(client2)
        
        client1.get("key")  # 无 Span
        client2.get("key")  # 有 Span
        """
        # 检查是否已埋点，避免重复
        if not hasattr(client, _INSTRUMENTATION_ATTR):
            setattr(client, _INSTRUMENTATION_ATTR, False)
        
        if not getattr(client, _INSTRUMENTATION_ATTR):
            _instrument_client(
                client,
                MyCacheInstrumentor._get_tracer(tracer_provider=tracer_provider),
                request_hook=request_hook,
                response_hook=response_hook,
            )
            setattr(client, _INSTRUMENTATION_ATTR, True)
        else:
            _logger.warning("尝试对已埋点的客户端实例再次埋点")
    
    @staticmethod
    def uninstrument_client(client: Any):
        """
        静态方法：卸载单个客户端实例的埋点
        """
        if getattr(client, _INSTRUMENTATION_ATTR, False):
            unwrap(client, "get")
            unwrap(client, "set")
            unwrap(client, "delete")
            setattr(client, _INSTRUMENTATION_ATTR, False)
        else:
            _logger.warning("尝试卸载未埋点的客户端实例")


# =============================================================================
# 导出
# =============================================================================

__all__ = ["MyCacheInstrumentor"]
