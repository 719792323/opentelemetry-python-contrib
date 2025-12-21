OpenTelemetry Demo MyCache Instrumentation（教学版）
=====================================================

这是一个教学性质的 OpenTelemetry Python Instrumentation 示例，
旨在帮助有 Java OT 经验的开发者快速理解 Python 的实现机制。

核心文件说明
-----------

::

    opentelemetry-instrumentation-demo-mycache/
    ├── pyproject.toml                    # 项目配置（类似 pom.xml）
    │                                     # - 声明 entry_points（类似 Java SPI）
    │                                     # - 声明 instruments 依赖
    │
    └── src/opentelemetry/instrumentation/demo_mycache/
        ├── __init__.py                   # 主模块
        │   ├── MyCacheInstrumentor       # 插件主类（类似 InstrumentationModule）
        │   ├── _instrument()             # 执行埋点（类似 TypeTransformer）
        │   ├── _traced_execute_factory   # 包装函数工厂（类似 Advice）
        │   └── _uninstrument()           # 卸载埋点（Python 特有）
        │
        ├── package.py                    # 依赖声明
        └── version.py                    # 版本号

与 Java 对比
-----------

+------------------+--------------------------------+--------------------------------+
| 功能             | Java                           | Python                         |
+------------------+--------------------------------+--------------------------------+
| 插件发现         | META-INF/services (SPI)        | entry_points                   |
| 依赖检测         | ClassLoader 类检测             | packaging 版本检测             |
| 方法拦截         | ByteBuddy + Advice             | wrapt.wrap_function_wrapper    |
| Span 创建        | spanBuilder().startSpan()      | start_as_current_span()        |
+------------------+--------------------------------+--------------------------------+

快速开始
--------

.. code-block:: python

    from opentelemetry.instrumentation.demo_mycache import MyCacheInstrumentor
    
    # 全局埋点
    MyCacheInstrumentor().instrument()
    
    # 使用缓存客户端（自动创建 Span）
    client = mycache.CacheClient()
    client.get("key")  # 自动创建 Span

运行演示
--------

.. code-block:: bash

    cd tests
    python demo_usage.py

参考资源
--------

- `OpenTelemetry Python 文档 <https://opentelemetry.io/docs/instrumentation/python/>`_
- `opentelemetry-instrumentation-redis 实现 <../opentelemetry-instrumentation-redis/>`_
