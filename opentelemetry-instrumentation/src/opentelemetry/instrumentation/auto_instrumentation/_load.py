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

from functools import cached_property
from logging import getLogger
from os import environ

from opentelemetry.instrumentation.dependencies import (
    DependencyConflictError,
    get_dist_dependency_conflicts,
)
from opentelemetry.instrumentation.distro import BaseDistro, DefaultDistro
from opentelemetry.instrumentation.environment_variables import (
    OTEL_PYTHON_CONFIGURATOR,
    OTEL_PYTHON_DISABLED_INSTRUMENTATIONS,
    OTEL_PYTHON_DISTRO,
)
from opentelemetry.instrumentation.version import __version__
from opentelemetry.util._importlib_metadata import (
    EntryPoint,
    distributions,
    entry_points,
)

_logger = getLogger(__name__)

SKIPPED_INSTRUMENTATIONS_WILDCARD = "*"


class _EntryPointDistFinder:
    @cached_property
    def _mapping(self):
        return {
            self._key_for(ep): dist
            for dist in distributions()
            for ep in dist.entry_points
        }

    def dist_for(self, entry_point: EntryPoint):
        dist = getattr(entry_point, "dist", None)
        if dist:
            return dist

        return self._mapping.get(self._key_for(entry_point))

    @staticmethod
    def _key_for(entry_point: EntryPoint):
        return f"{entry_point.group}:{entry_point.name}:{entry_point.value}"


def _load_distro() -> BaseDistro:
    distro_name = environ.get(OTEL_PYTHON_DISTRO, None)
    for entry_point in entry_points(group="opentelemetry_distro"):
        try:
            # If no distro is specified, use first to come up.
            if distro_name is None or distro_name == entry_point.name:
                distro = entry_point.load()()
                if not isinstance(distro, BaseDistro):
                    _logger.debug(
                        "%s is not an OpenTelemetry Distro. Skipping",
                        entry_point.name,
                    )
                    continue
                _logger.debug(
                    "Distribution %s will be configured", entry_point.name
                )
                return distro
        except Exception as exc:  # pylint: disable=broad-except
            _logger.exception(
                "Distribution %s configuration failed", entry_point.name
            )
            raise exc
    return DefaultDistro()


def _load_instrumentors(distro):
    """
    加载并启用所有可用的 OpenTelemetry 插桩器
    
    这是自动插桩的核心函数，负责：
    1. 发现所有已安装的插桩器
    2. 检查依赖冲突
    3. 启用插桩器为对应的库添加追踪功能
    
    参数:
        distro: BaseDistro 实例，用于加载插桩器
    """
    
    # ============================================================================
    # 步骤 1: 处理禁用的插桩器列表
    # ============================================================================
    # 功能：允许用户通过环境变量禁用特定的插桩器
    #
    # 使用场景：
    #   - 某个库的插桩器有 bug，需要临时禁用
    #   - 某个库不需要追踪，减少性能开销
    #   - 测试时只想启用部分插桩器
    #
    # 例子 1: 禁用单个插桩器
    #   export OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=requests
    #   结果: requests 库不会被插桩，其他库正常插桩
    #
    # 例子 2: 禁用多个插桩器
    #   export OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=requests,flask,redis
    #   结果: requests、flask、redis 都不会被插桩
    #
    # 例子 3: 禁用所有插桩器
    #   export OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=*
    #   结果: 所有插桩器都被禁用（通常用于调试）
    #
    # 例子 4: 处理空格（用户友好）
    #   export OTEL_PYTHON_DISABLED_INSTRUMENTATIONS="requests , flask , redis"
    #   结果: 自动去除空格，等同于 "requests,flask,redis"
    # ============================================================================
    package_to_exclude = environ.get(OTEL_PYTHON_DISABLED_INSTRUMENTATIONS, [])
    entry_point_finder = _EntryPointDistFinder()
    
    # 将字符串转换为列表，并去除空格
    if isinstance(package_to_exclude, str):
        package_to_exclude = package_to_exclude.split(",")
        # to handle users entering "requests , flask" or "requests, flask" with spaces
        package_to_exclude = [x.strip() for x in package_to_exclude]
    
    # ============================================================================
    # 步骤 2: 执行预插桩钩子（Pre-Instrument Hooks）
    # ============================================================================
    # 功能：在所有插桩器加载之前执行自定义逻辑
    #
    # 工作原理：
    #   1. 通过 Entry Point "opentelemetry_pre_instrument" 发现所有钩子
    #   2. 按顺序加载并执行每个钩子函数
    #
    # 使用场景：
    #   - 设置全局配置
    #   - 初始化共享资源
    #   - 修改环境变量
    #   - 注册自定义的 span processor
    #
    # 例子：创建一个预插桩钩子
    #   # my_package/hooks.py
    #   def pre_instrument_hook():
    #       print("准备开始插桩...")
    #       os.environ['CUSTOM_CONFIG'] = 'value'
    #   
    #   # setup.py
    #   entry_points={
    #       'opentelemetry_pre_instrument': [
    #           'my_hook = my_package.hooks:pre_instrument_hook',
    #       ],
    #   }
    #
    # 执行顺序：
    #   pre_instrument_hook_1() -> pre_instrument_hook_2() -> ... -> 开始插桩
    # ============================================================================
    for entry_point in entry_points(group="opentelemetry_pre_instrument"):
        entry_point.load()()  # 加载并立即执行钩子函数
    
    # ============================================================================
    # 步骤 3: 遍历并加载所有插桩器（核心逻辑）
    # ============================================================================
    # 功能：发现、验证并启用所有可用的插桩器
    #
    # Entry Point 机制：
    #   插桩器通过 Entry Point "opentelemetry_instrumentor" 注册
    #   
    #   例子：Flask 插桩器的注册
    #   # opentelemetry-instrumentation-flask/setup.py
    #   entry_points={
    #       'opentelemetry_instrumentor': [
    #           'flask = opentelemetry.instrumentation.flask:FlaskInstrumentor',
    #       ],
    #   }
    #
    # 发现的插桩器示例：
    #   entry_point.name = "flask"
    #   entry_point.value = "opentelemetry.instrumentation.flask:FlaskInstrumentor"
    #   entry_point.group = "opentelemetry_instrumentor"
    # ============================================================================
    for entry_point in entry_points(group="opentelemetry_instrumentor"):
        
        # ------------------------------------------------------------------------
        # 检查 1: 是否禁用了所有插桩器
        # ------------------------------------------------------------------------
        # 如果环境变量设置为 "*"，则跳过所有插桩器
        #
        # 例子：
        #   export OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=*
        #   结果: 直接 break，不加载任何插桩器
        # ------------------------------------------------------------------------
        if SKIPPED_INSTRUMENTATIONS_WILDCARD in package_to_exclude:
            break
        
        # ------------------------------------------------------------------------
        # 检查 2: 是否禁用了当前插桩器
        # ------------------------------------------------------------------------
        # 检查当前插桩器是否在禁用列表中
        #
        # 例子：
        #   package_to_exclude = ["requests", "flask"]
        #   当前 entry_point.name = "flask"
        #   结果: 跳过 Flask 插桩器，继续处理下一个
        # ------------------------------------------------------------------------
        if entry_point.name in package_to_exclude:
            _logger.debug(
                "Instrumentation skipped for library %s", entry_point.name
            )
            continue
        
        try:
            # --------------------------------------------------------------------
            # 检查 3: 依赖冲突检测
            # --------------------------------------------------------------------
            # 功能：检查插桩器的依赖版本是否与已安装的库版本兼容
            #
            # 工作原理：
            #   1. 获取插桩器的 distribution 信息
            #   2. 检查插桩器声明的依赖版本要求
            #   3. 与实际安装的库版本进行比对
            #
            # 例子 1: 版本兼容
            #   插桩器要求: flask >= 2.0.0, < 3.0.0
            #   实际安装: flask 2.3.0
            #   结果: 无冲突，继续加载
            #
            # 例子 2: 版本不兼容
            #   插桩器要求: flask >= 2.0.0, < 3.0.0
            #   实际安装: flask 1.1.4
            #   结果: 检测到冲突，跳过该插桩器
            #   日志: "Skipping instrumentation flask: requires flask>=2.0.0 but 1.1.4 is installed"
            #
            # 例子 3: 库未安装
            #   插桩器: django
            #   实际安装: 未安装 django
            #   结果: 跳过该插桩器（后续会捕获 ModuleNotFoundError）
            # --------------------------------------------------------------------
            entry_point_dist = entry_point_finder.dist_for(entry_point)
            conflict = get_dist_dependency_conflicts(entry_point_dist)
            if conflict:
                _logger.debug(
                    "Skipping instrumentation %s: %s",
                    entry_point.name,
                    conflict,
                )
                continue
            
            # --------------------------------------------------------------------
            # 步骤 4: 加载并启用插桩器
            # --------------------------------------------------------------------
            # 功能：实例化插桩器并调用其 instrument() 方法
            #
            # 工作流程：
            #   1. distro.load_instrumentor() 加载插桩器类
            #   2. 实例化插桩器（例如 FlaskInstrumentor()）
            #   3. 调用 instrumentor.instrument() 方法
            #   4. 插桩器通过 monkey patching 修改目标库的行为
            #
            # 例子：Flask 插桩器的加载过程
            #   
            #   # 1. 加载 FlaskInstrumentor 类
            #   FlaskInstrumentor = entry_point.load()
            #   
            #   # 2. 实例化
            #   instrumentor = FlaskInstrumentor()
            #   
            #   # 3. 启用插桩
            #   instrumentor.instrument()
            #   
            #   # 4. Flask 的行为被修改
            #   #    原始代码:
            #   @app.route('/users')
            #   def get_users():
            #       return {'users': [...]}
            #   
            #   #    插桩后自动添加:
            #   @app.route('/users')
            #   def get_users():
            #       with tracer.start_as_current_span('GET /users'):  # 自动添加
            #           return {'users': [...]}
            #
            # skip_dep_check=True 的原因：
            #   我们已经在上面执行了依赖检查，避免重复检查提高性能
            # --------------------------------------------------------------------
            # tell instrumentation to not run dep checks again as we already did it above
            distro.load_instrumentor(entry_point, skip_dep_check=True)
            _logger.debug("Instrumented %s", entry_point.name)
            
        # ------------------------------------------------------------------------
        # 异常处理 1: DependencyConflictError
        # ------------------------------------------------------------------------
        # 场景：自定义 distro 或插桩器在后续阶段抛出依赖冲突错误
        #
        # 例子：
        #   某个自定义插桩器在 instrument() 方法中检查版本
        #   if flask_version < '2.0':
        #       raise DependencyConflictError("Flask >= 2.0 required")
        #
        # 处理：记录日志并跳过该插桩器，继续处理其他插桩器
        # ------------------------------------------------------------------------
        except DependencyConflictError as exc:
            # Dependency conflicts are generally caught from get_dist_dependency_conflicts
            # returning a DependencyConflict. Keeping this error handling in case custom
            # distro and instrumentor behavior raises a DependencyConflictError later.
            # See https://github.com/open-telemetry/opentelemetry-python-contrib/pull/3610
            _logger.debug(
                "Skipping instrumentation %s: %s",
                entry_point.name,
                exc.conflict,
            )
            continue
        
        # ------------------------------------------------------------------------
        # 异常处理 2: ModuleNotFoundError
        # ------------------------------------------------------------------------
        # 场景：目标库未安装，插桩器无法加载
        #
        # 例子 1: Django 插桩器但未安装 Django
        #   entry_point.name = "django"
        #   执行 entry_point.load() 时尝试 import django
        #   抛出 ModuleNotFoundError: No module named 'django'
        #   结果: 跳过该插桩器
        #
        # 例子 2: 实际场景
        #   你的应用只使用 Flask 和 Requests
        #   系统发现了 20 个插桩器（flask, requests, django, fastapi, ...）
        #   只有 flask 和 requests 会被加载
        #   其他 18 个会因为 ModuleNotFoundError 被跳过
        #
        # 这是正常行为：插桩器会尝试加载所有已注册的插桩器，
        # 但只有对应库已安装的插桩器才会真正启用
        # ------------------------------------------------------------------------
        except ModuleNotFoundError as exc:
            # ModuleNotFoundError is raised when the library is not installed
            # and the instrumentation is not required to be loaded.
            # See https://github.com/open-telemetry/opentelemetry-python-contrib/issues/3421
            _logger.debug(
                "Skipping instrumentation %s: %s", entry_point.name, exc.msg
            )
            continue
        
        # ------------------------------------------------------------------------
        # 异常处理 3: ImportError
        # ------------------------------------------------------------------------
        # 场景：插桩器加载失败，但不是因为库未安装
        #
        # 典型场景：Kubernetes Operator 自动插桩
        #   问题：
        #     - Operator 注入的插桩代码可能与应用环境不匹配
        #     - Python 版本不同（注入的是 3.11，应用是 3.9）
        #     - libc 版本不同（注入的是 glibc 2.31，应用是 2.28）
        #     - 二进制扩展不兼容（如 psycopg2-binary）
        #
        # 例子：
        #   Operator 注入的 psycopg2 插桩器需要 libpq.so.5
        #   但容器中只有 libpq.so.4
        #   抛出 ImportError: libpq.so.5: cannot open shared object file
        #
        # 处理策略：
        #   - 记录详细的异常日志（包括堆栈跟踪）
        #   - 跳过该插桩器，继续处理其他插桩器
        #   - 不抛出异常，避免整个应用启动失败
        #
        # 设计理念：
        #   "部分插桩失败" 优于 "完全无法启动"
        #   即使某些插桩器失败，其他插桩器仍然可以工作
        # ------------------------------------------------------------------------
        except ImportError:
            # in scenarios using the kubernetes operator to do autoinstrumentation some
            # instrumentors (usually requiring binary extensions) may fail to load
            # because the injected autoinstrumentation code does not match the application
            # environment regarding python version, libc, etc... In this case it's better
            # to skip the single instrumentation rather than failing to load everything
            # so treat differently ImportError than the rest of exceptions
            _logger.exception(
                "Importing of %s failed, skipping it", entry_point.name
            )
            continue
        
        # ------------------------------------------------------------------------
        # 异常处理 4: 其他所有异常
        # ------------------------------------------------------------------------
        # 场景：未预期的严重错误
        #
        # 例子：
        #   - 插桩器代码有 bug（NullPointerError、AttributeError 等）
        #   - 内存不足
        #   - 文件系统错误
        #
        # 处理：
        #   - 记录详细的异常日志
        #   - 抛出异常，停止整个插桩过程
        #
        # 设计理念：
        #   这些错误通常表示严重问题，应该立即暴露给开发者
        #   而不是静默失败
        # ------------------------------------------------------------------------
        except Exception as exc:  # pylint: disable=broad-except
            _logger.exception("Instrumenting of %s failed", entry_point.name)
            raise exc
    
    # ============================================================================
    # 步骤 5: 执行后插桩钩子（Post-Instrument Hooks）
    # ============================================================================
    # 功能：在所有插桩器加载完成后执行自定义逻辑
    #
    # 工作原理：
    #   1. 通过 Entry Point "opentelemetry_post_instrument" 发现所有钩子
    #   2. 按顺序加载并执行每个钩子函数
    #
    # 使用场景：
    #   - 验证插桩是否成功
    #   - 发送启动完成的通知
    #   - 记录插桩统计信息
    #   - 执行清理工作
    #
    # 例子：创建一个后插桩钩子
    #   # my_package/hooks.py
    #   def post_instrument_hook():
    #       print("所有插桩器已加载完成！")
    #       # 发送指标
    #       metrics.gauge('instrumentation.loaded', len(loaded_instrumentors))
    #   
    #   # setup.py
    #   entry_points={
    #       'opentelemetry_post_instrument': [
    #           'my_hook = my_package.hooks:post_instrument_hook',
    #       ],
    #   }
    #
    # 执行顺序：
    #   所有插桩器加载完成 -> post_instrument_hook_1() -> post_instrument_hook_2() -> ...
    #
    # 完整的执行流程：
    #   pre_instrument hooks
    #   -> 加载插桩器 1 (flask)
    #   -> 加载插桩器 2 (requests)
    #   -> 加载插桩器 3 (redis)
    #   -> ...
    #   -> post_instrument hooks
    # ============================================================================
    for entry_point in entry_points(group="opentelemetry_post_instrument"):
        entry_point.load()()  # 加载并立即执行钩子函数


def _load_configurators():
    configurator_name = environ.get(OTEL_PYTHON_CONFIGURATOR, None)
    configured = None
    for entry_point in entry_points(group="opentelemetry_configurator"):
        if configured is not None:
            _logger.warning(
                "Configuration of %s not loaded, %s already loaded",
                entry_point.name,
                configured,
            )
            continue
        try:
            if (
                configurator_name is None
                or configurator_name == entry_point.name
            ):
                entry_point.load()().configure(
                    auto_instrumentation_version=__version__
                )  # type: ignore
                configured = entry_point.name
            else:
                _logger.warning(
                    "Configuration of %s not loaded because %s is set by %s",
                    entry_point.name,
                    configurator_name,
                    OTEL_PYTHON_CONFIGURATOR,
                )
        except Exception as exc:  # pylint: disable=broad-except
            _logger.exception("Configuration of %s failed", entry_point.name)
            raise exc
