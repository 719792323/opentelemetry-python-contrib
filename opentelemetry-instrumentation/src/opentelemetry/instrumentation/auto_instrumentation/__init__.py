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

from __future__ import annotations

from argparse import REMAINDER, ArgumentParser
from logging import getLogger
from os import environ, execl, getcwd
from os.path import abspath, dirname, pathsep
from re import sub
from shutil import which

from opentelemetry.instrumentation.auto_instrumentation._load import (
    _load_configurators,
    _load_distro,
    _load_instrumentors,
)
from opentelemetry.instrumentation.environment_variables import (
    OTEL_PYTHON_AUTO_INSTRUMENTATION_EXPERIMENTAL_GEVENT_PATCH,
)
from opentelemetry.instrumentation.utils import _python_path_without_directory
from opentelemetry.instrumentation.version import __version__
from opentelemetry.util._importlib_metadata import entry_points

_logger = getLogger(__name__)


def run() -> None:
    """
    opentelemetry-instrument 命令的主入口函数
    
    功能：解析命令行参数，设置环境变量，然后执行目标 Python 程序
    
    完整执行流程示例：
    ==================
    
    假设用户执行命令：
    $ opentelemetry-instrument --service_name=my-app --traces_exporter=console python app.py --port 8080
    
    执行步骤：
    1. 创建参数解析器
    2. 动态添加所有 OTEL 环境变量对应的命令行参数
    3. 解析命令行参数
    4. 将参数值设置到环境变量
    5. 修改 PYTHONPATH，注入 sitecustomize.py
    6. 使用 execl 替换当前进程，执行目标程序
    
    最终效果：
    - 环境变量 OTEL_SERVICE_NAME=my-app
    - 环境变量 OTEL_TRACES_EXPORTER=console
    - PYTHONPATH 包含 sitecustomize.py 所在目录
    - 执行 python app.py --port 8080
    - sitecustomize.py 会在 Python 启动时自动加载，完成自动埋点
    """
    
    # ============================================================================
    # 步骤 1：创建命令行参数解析器
    # ============================================================================
    # 作用：定义 opentelemetry-instrument 命令的帮助信息和基本结构
    # 
    # 示例：用户执行 opentelemetry-instrument --help 时会显示这些信息
    parser = ArgumentParser(
        description="""
        opentelemetry-instrument automatically instruments a Python
        program and its dependencies and then runs the program.
        """,
        epilog="""
        Optional arguments (except for --help and --version) for opentelemetry-instrument
        directly correspond with OpenTelemetry environment variables. The
        corresponding optional argument is formed by removing the OTEL_ or
        OTEL_PYTHON_ prefix from the environment variable and lower casing the
        rest. For example, the optional argument --attribute_value_length_limit
        corresponds with the environment variable
        OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT.

        These optional arguments will override the current value of the
        corresponding environment variable during the execution of the command.
        """,
    )

    # ============================================================================
    # 步骤 2：动态添加所有 OTEL 环境变量对应的命令行参数
    # ============================================================================
    # 作用：自动发现所有 OTEL 环境变量，并为每个变量创建对应的命令行参数
    # 
    # 工作原理：
    # 1. 通过 entry_points 机制查找所有注册的环境变量模块
    # 2. 扫描模块中所有以 OTEL_ 开头的常量
    # 3. 将环境变量名转换为命令行参数名
    # 4. 建立参数名和环境变量名的映射关系
    #
    # 示例转换规则：
    # - OTEL_SERVICE_NAME          → --service_name
    # - OTEL_TRACES_EXPORTER       → --traces_exporter
    # - OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED → --logging_auto_instrumentation_enabled
    #
    # 转换步骤：
    # 1. 移除 OTEL_ 或 OTEL_PYTHON_ 前缀
    # 2. 转换为小写
    # 3. 添加 -- 前缀
    argument_otel_environment_variable = {}

    # 遍历所有注册的环境变量模块
    # 示例：opentelemetry.sdk.environment_variables, opentelemetry.instrumentation.environment_variables
    for entry_point in entry_points(
        group="opentelemetry_environment_variables"
    ):
        # 加载模块
        # 示例：加载 opentelemetry.sdk.environment_variables 模块
        environment_variable_module = entry_point.load()

        # 遍历模块中的所有属性
        # 示例：OTEL_SERVICE_NAME, OTEL_TRACES_EXPORTER, OTEL_METRICS_EXPORTER 等
        for attribute in dir(environment_variable_module):
            if attribute.startswith("OTEL_"):
                # 转换环境变量名为命令行参数名
                # 示例：
                # - OTEL_SERVICE_NAME → service_name
                # - OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED → logging_auto_instrumentation_enabled
                argument = sub(r"OTEL_(PYTHON_)?", "", attribute).lower()

                # 添加命令行参数
                # 示例：parser.add_argument("--service_name", required=False)
                parser.add_argument(
                    f"--{argument}",
                    required=False,
                )
                
                # 建立映射关系：参数名 → 环境变量名
                # 示例：{"service_name": "OTEL_SERVICE_NAME", "traces_exporter": "OTEL_TRACES_EXPORTER"}
                argument_otel_environment_variable[argument] = attribute

    # 添加 --version 参数
    # 示例：opentelemetry-instrument --version
    # 输出：opentelemetry-instrument 0.61b0.dev
    parser.add_argument(
        "--version",
        help="print version information",
        action="version",
        version="%(prog)s " + __version__,
    )
    
    # 添加位置参数：command（要执行的命令）
    # 示例：python, flask, django-admin 等
    parser.add_argument("command", help="Your Python application.")
    
    # 添加位置参数：command_args（传递给目标程序的参数）
    # nargs=REMAINDER 表示捕获所有剩余的参数
    # 示例：app.py --port 8080 --debug
    parser.add_argument(
        "command_args",
        help="Arguments for your application.",
        nargs=REMAINDER,
    )

    # ============================================================================
    # 步骤 3：解析命令行参数
    # ============================================================================
    # 作用：将用户输入的命令行参数解析为 Python 对象
    #
    # 示例输入：
    # $ opentelemetry-instrument --service_name=my-app --traces_exporter=console python app.py --port 8080
    #
    # 解析结果（args 对象）：
    # args.service_name = "my-app"
    # args.traces_exporter = "console"
    # args.command = "python"
    # args.command_args = ["app.py", "--port", "8080"]
    args = parser.parse_args()

    # ============================================================================
    # 步骤 4：将命令行参数值设置到环境变量
    # ============================================================================
    # 作用：将用户通过命令行传递的参数值设置为对应的环境变量
    #
    # 工作原理：
    # 1. 遍历所有参数名和环境变量名的映射
    # 2. 获取参数的值
    # 3. 如果值不为 None，则设置到环境变量
    #
    # 示例：
    # 输入：--service_name=my-app --traces_exporter=console
    # 
    # 循环处理：
    # 第 1 次循环：
    #   argument = "service_name"
    #   otel_environment_variable = "OTEL_SERVICE_NAME"
    #   value = "my-app"
    #   设置：environ["OTEL_SERVICE_NAME"] = "my-app"
    #
    # 第 2 次循环：
    #   argument = "traces_exporter"
    #   otel_environment_variable = "OTEL_TRACES_EXPORTER"
    #   value = "console"
    #   设置：environ["OTEL_TRACES_EXPORTER"] = "console"
    #
    # 结果：目标程序启动时可以通过 os.environ 读取这些配置
    for argument, otel_environment_variable in (
        argument_otel_environment_variable
    ).items():
        value = getattr(args, argument)
        if value is not None:
            environ[otel_environment_variable] = value

    # ============================================================================
    # 步骤 5：修改 PYTHONPATH，注入 sitecustomize.py
    # ============================================================================
    # 作用：将 sitecustomize.py 所在目录添加到 PYTHONPATH 的最前面
    #
    # 为什么要修改 PYTHONPATH？
    # - Python 启动时会自动导入 sitecustomize.py（如果存在）
    # - sitecustomize.py 会调用 initialize() 函数完成自动埋点
    # - 通过修改 PYTHONPATH，确保 Python 能找到我们的 sitecustomize.py
    #
    # 示例场景：
    # 假设：
    # - 当前目录：/home/user/myapp
    # - sitecustomize.py 位于：/usr/lib/python3.9/site-packages/opentelemetry/instrumentation/auto_instrumentation/
    # - 原始 PYTHONPATH：/home/user/lib:/usr/local/lib
    
    # 5.1 获取当前的 PYTHONPATH
    # 示例：python_path = "/home/user/lib:/usr/local/lib"
    python_path = environ.get("PYTHONPATH")

    # 5.2 将 PYTHONPATH 转换为列表
    # 如果 PYTHONPATH 为空，初始化为空列表
    # 示例：python_path = []
    if not python_path:
        python_path = []
    else:
        # 如果 PYTHONPATH 不为空，按路径分隔符分割
        # 示例：python_path = ["/home/user/lib", "/usr/local/lib"]
        python_path = python_path.split(pathsep)

    # 5.3 获取当前工作目录
    # 示例：cwd_path = "/home/user/myapp"
    cwd_path = getcwd()

    # 5.4 将当前工作目录添加到 PYTHONPATH（如果不存在）
    # 作用：支持从当前目录导入模块（特别是 Django 等框架）
    #
    # 示例：
    # 如果 cwd_path = "/home/user/myapp" 不在 python_path 中
    # 则：python_path = ["/home/user/myapp", "/home/user/lib", "/usr/local/lib"]
    if cwd_path not in python_path:
        python_path.insert(0, cwd_path)

    # 5.5 获取 sitecustomize.py 所在目录
    # __file__ 是当前文件的路径
    # 示例：
    # __file__ = "/usr/lib/python3.9/site-packages/opentelemetry/instrumentation/auto_instrumentation/__init__.py"
    # filedir_path = "/usr/lib/python3.9/site-packages/opentelemetry/instrumentation/auto_instrumentation"
    filedir_path = dirname(abspath(__file__))

    # 5.6 从 PYTHONPATH 中移除 sitecustomize.py 所在目录（如果存在）
    # 作用：避免重复添加
    # 示例：python_path = ["/home/user/myapp", "/home/user/lib", "/usr/local/lib"]
    python_path = [path for path in python_path if path != filedir_path]

    # 5.7 将 sitecustomize.py 所在目录添加到 PYTHONPATH 的最前面
    # 作用：确保 Python 优先加载我们的 sitecustomize.py
    # 示例：
    # python_path = [
    #     "/usr/lib/python3.9/site-packages/opentelemetry/instrumentation/auto_instrumentation",
    #     "/home/user/myapp",
    #     "/home/user/lib",
    #     "/usr/local/lib"
    # ]
    python_path.insert(0, filedir_path)

    # 5.8 将列表转换回字符串，并设置到环境变量
    # 示例：
    # environ["PYTHONPATH"] = "/usr/lib/.../auto_instrumentation:/home/user/myapp:/home/user/lib:/usr/local/lib"
    environ["PYTHONPATH"] = pathsep.join(python_path)

    # ============================================================================
    # 步骤 6：使用 execl 替换当前进程，执行目标程序
    # ============================================================================
    # 作用：用目标程序替换当前进程
    #
    # 工作原理：
    # 1. 使用 which() 查找命令的完整路径
    # 2. 使用 execl() 替换当前进程
    #
    # 示例：
    # args.command = "python"
    # args.command_args = ["app.py", "--port", "8080"]
    #
    # 步骤 6.1：查找 python 的完整路径
    # executable = which("python")
    # 结果：executable = "/usr/bin/python3"
    executable = which(args.command)
    
    # 步骤 6.2：替换当前进程
    # execl("/usr/bin/python3", "/usr/bin/python3", "app.py", "--port", "8080")
    #
    # 执行效果：
    # - 当前进程被替换为 python 进程
    # - 执行命令：/usr/bin/python3 app.py --port 8080
    # - 环境变量已设置：OTEL_SERVICE_NAME=my-app, OTEL_TRACES_EXPORTER=console
    # - PYTHONPATH 已修改，包含 sitecustomize.py 所在目录
    # - Python 启动时会自动导入 sitecustomize.py
    # - sitecustomize.py 调用 initialize() 完成自动埋点
    # - 最终 app.py 在已埋点的环境中运行
    #
    # 注意：execl 不会返回，当前进程会被完全替换
    execl(executable, executable, *args.command_args)


def initialize(*, swallow_exceptions: bool = True) -> None:
    """
    Setup auto-instrumentation, called by the sitecustomize module

    :param swallow_exceptions: Whether or not to propagate instrumentation exceptions to the caller. Exceptions are logged and swallowed by default.
    """
    # ============================================================================
    # 步骤 1: 防止子进程的自动插桩
    # ============================================================================
    # 问题场景：当你的 Python 程序使用 subprocess 或 os.system 启动另一个 Python 进程时，
    # 如果 PYTHONPATH 中包含 sitecustomize.py 所在目录，子进程也会被自动插桩
    #
    # 例子：
    #   主进程: opentelemetry-instrument python app.py
    #   PYTHONPATH=/path/to/opentelemetry/auto_instrumentation:/other/paths
    #   
    #   如果 app.py 中执行: subprocess.run(['python', 'worker.py'])
    #   子进程 worker.py 也会触发 sitecustomize.py，导致重复插桩
    #
    # 解决方案：从 PYTHONPATH 中移除 sitecustomize.py 所在的目录
    #
    # 示例：
    #   原始 PYTHONPATH: /path/to/auto_instrumentation:/home/user/mylib
    #   处理后 PYTHONPATH: /home/user/mylib
    #   (移除了 /path/to/auto_instrumentation)
    # ============================================================================
    if "PYTHONPATH" in environ:
        environ["PYTHONPATH"] = _python_path_without_directory(
            environ["PYTHONPATH"], dirname(abspath(__file__)), pathsep
        )

    # ============================================================================
    # 步骤 2: 处理可选的 gevent monkey patching
    # ============================================================================
    # gevent 是一个协程库，需要在程序启动时"打补丁"来替换标准库的阻塞操作
    # 
    # 使用场景：
    #   - 你的应用使用 gevent 进行异步编程
    #   - 需要在 OpenTelemetry 插桩之前先打 gevent 补丁
    #   - 通过环境变量控制，方便在 Kubernetes Operator 中使用
    #
    # 例子：
    #   export OTEL_PYTHON_AUTO_INSTRUMENTATION_EXPERIMENTAL_GEVENT_PATCH=patch_all
    #   opentelemetry-instrument python gevent_app.py
    #
    # 执行流程：
    #   1. 检查环境变量 OTEL_PYTHON_AUTO_INSTRUMENTATION_EXPERIMENTAL_GEVENT_PATCH
    #   2. 如果值为 "patch_all"，则调用 gevent.monkey.patch_all()
    #   3. 如果值不是 "patch_all"，记录错误日志
    #   4. 如果 gevent 未安装，记录异常并根据 swallow_exceptions 决定是否抛出
    # ============================================================================
    gevent_patch: str | None = environ.get(
        OTEL_PYTHON_AUTO_INSTRUMENTATION_EXPERIMENTAL_GEVENT_PATCH
    )
    if gevent_patch is not None:
        # 验证环境变量值必须是 "patch_all"
        if gevent_patch != "patch_all":
            _logger.error(
                "%s value must be `patch_all`",
                OTEL_PYTHON_AUTO_INSTRUMENTATION_EXPERIMENTAL_GEVENT_PATCH,
            )
        else:
            try:
                # 动态导入 gevent 并执行 monkey.patch_all()
                # 这会替换标准库的 socket, threading, time 等模块
                # pylint: disable=import-outside-toplevel
                from gevent import monkey  # noqa: PLC0415

                getattr(monkey, gevent_patch)()  # 等价于 monkey.patch_all()
            except ImportError:
                # gevent 未安装时的处理
                _logger.exception(
                    "Failed to monkey patch with gevent because gevent is not available"
                )
                if not swallow_exceptions:
                    raise

    # ============================================================================
    # 步骤 3: 加载和配置 OpenTelemetry 组件
    # ============================================================================
    # 这是核心的自动插桩逻辑，分为 4 个子步骤
    #
    # 例子场景：
    #   你的应用使用了 Flask、Requests、Redis
    #   OpenTelemetry 需要自动为这些库添加追踪功能
    #
    # 执行流程：
    # ============================================================================
    try:
        # ------------------------------------------------------------------------
        # 步骤 3.1: 加载 Distro（发行版）
        # ------------------------------------------------------------------------
        # Distro 是 OpenTelemetry 的"发行版"，可以自定义默认配置
        #
        # 例子：
        #   - 默认使用 opentelemetry.sdk._configuration.OpenTelemetryDistro
        #   - 可以通过 Entry Point 注册自定义 Distro
        #   - 自定义 Distro 可以预设 exporter、processor 等
        #
        # 返回值：
        #   distro = OpenTelemetryDistro() 实例
        # ------------------------------------------------------------------------
        distro = _load_distro()
        
        # ------------------------------------------------------------------------
        # 步骤 3.2: 配置 Distro
        # ------------------------------------------------------------------------
        # 调用 distro.configure() 方法，执行以下操作：
        #   1. 读取环境变量（OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT 等）
        #   2. 初始化 TracerProvider、MeterProvider、LoggerProvider
        #   3. 配置 Exporter（如 OTLP、Jaeger、Zipkin）
        #   4. 配置 Processor（如 BatchSpanProcessor）
        #   5. 配置 Sampler（如 AlwaysOn、TraceIdRatioBased）
        #
        # 例子：
        #   环境变量:
        #     OTEL_SERVICE_NAME=my-flask-app
        #     OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
        #   
        #   执行后:
        #     - 创建 TracerProvider，service.name = "my-flask-app"
        #     - 配置 OTLPSpanExporter，发送到 localhost:4317
        #     - 注册为全局 TracerProvider
        # ------------------------------------------------------------------------
        distro.configure()
        
        # ------------------------------------------------------------------------
        # 步骤 3.3: 加载配置器（Configurators）
        # ------------------------------------------------------------------------
        # Configurators 是额外的配置钩子，用于自定义初始化逻辑
        #
        # 工作原理：
        #   1. 通过 Entry Point "opentelemetry_configurator" 发现所有配置器
        #   2. 按顺序调用每个配置器的 configure() 方法
        #
        # 例子：
        #   你可以创建自定义配置器来：
        #   - 添加自定义的 SpanProcessor
        #   - 设置特定的资源属性
        #   - 配置日志格式
        #
        # Entry Point 示例：
        #   [project.entry-points.opentelemetry_configurator]
        #   my_configurator = "mypackage.configurator:MyConfigurator"
        # ------------------------------------------------------------------------
        _load_configurators()
        
        # ------------------------------------------------------------------------
        # 步骤 3.4: 加载并启用插桩器（Instrumentors）
        # ------------------------------------------------------------------------
        # 这是最关键的一步：自动为已安装的库添加追踪功能
        #
        # 工作原理：
        #   1. 通过 Entry Point "opentelemetry_instrumentor" 发现所有插桩器
        #   2. 检查每个插桩器对应的库是否已安装
        #   3. 如果已安装，调用 instrumentor.instrument() 启用插桩
        #
        # 例子：
        #   已安装的库: flask, requests, redis
        #   
        #   发现的插桩器:
        #     - FlaskInstrumentor (flask 已安装) ✅
        #     - RequestsInstrumentor (requests 已安装) ✅
        #     - RedisInstrumentor (redis 已安装) ✅
        #     - DjangoInstrumentor (django 未安装) ❌ 跳过
        #   
        #   执行结果:
        #     - Flask 的路由处理会自动创建 span
        #     - requests.get() 会自动创建 HTTP 客户端 span
        #     - Redis 命令会自动创建 span
        #
        # 插桩效果：
        #   原始代码:
        #     @app.route('/api/users')
        #     def get_users():
        #         response = requests.get('http://api.example.com/users')
        #         redis_client.set('cache_key', response.text)
        #         return response.json()
        #   
        #   插桩后自动生成的 trace:
        #     Span 1: GET /api/users (Flask)
        #       └─ Span 2: HTTP GET http://api.example.com/users (Requests)
        #       └─ Span 3: redis.set cache_key (Redis)
        # ------------------------------------------------------------------------
        _load_instrumentors(distro)
        
    except Exception as exc:  # pylint: disable=broad-except
        # ------------------------------------------------------------------------
        # 步骤 4: 异常处理
        # ------------------------------------------------------------------------
        # 如果自动插桩过程中出现任何异常：
        #   1. 记录详细的异常日志（包括堆栈跟踪）
        #   2. 根据 swallow_exceptions 参数决定是否抛出异常
        #
        # swallow_exceptions=True (默认):
        #   - 吞掉异常，应用继续运行（但没有追踪功能）
        #   - 适用于生产环境，避免因插桩失败导致应用崩溃
        #
        # swallow_exceptions=False:
        #   - 抛出异常，应用启动失败
        #   - 适用于开发/测试环境，快速发现配置问题
        #
        # 例子：
        #   场景 1: OTLP Exporter 配置错误
        #     - swallow_exceptions=True: 应用正常启动，但无法发送 trace
        #     - swallow_exceptions=False: 应用启动失败，立即发现问题
        #
        #   场景 2: 某个插桩器版本不兼容
        #     - swallow_exceptions=True: 跳过该插桩器，其他插桩器正常工作
        #     - swallow_exceptions=False: 应用启动失败，需要修复兼容性问题
        # ------------------------------------------------------------------------
        _logger.exception("Failed to auto initialize OpenTelemetry")
        if not swallow_exceptions:
            raise exc
