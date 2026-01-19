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

import argparse
import logging
import sys
from subprocess import (
    PIPE,
    CalledProcessError,
    Popen,
    SubprocessError,
    check_call,
)
from typing import Optional

from packaging.requirements import Requirement

from opentelemetry.instrumentation.bootstrap_gen import (
    default_instrumentations as gen_default_instrumentations,
)
from opentelemetry.instrumentation.bootstrap_gen import (
    libraries as gen_libraries,
)
from opentelemetry.instrumentation.version import __version__
from opentelemetry.util._importlib_metadata import (
    PackageNotFoundError,
    version,
)

logger = logging.getLogger(__name__)


def _syscall(func):
    def wrapper(package=None):
        try:
            if package:
                return func(package)
            return func()
        except SubprocessError as exp:
            cmd = getattr(exp, "cmd", None)
            if cmd:
                msg = f'Error calling system command "{" ".join(cmd)}"'
            if package:
                msg = f'{msg} for package "{package}"'
            raise RuntimeError(msg)

    return wrapper


@_syscall
def _sys_pip_install(package):
    """
    使用 pip 安装指定的包
    
    核心功能：
    1. 调用系统的 pip 命令安装包
    2. 使用当前 Python 解释器对应的 pip
    3. 采用保守的升级策略，避免破坏现有依赖
    
    参数说明：
    - package: 要安装的包名称，可以包含版本约束
               例如: "opentelemetry-instrumentation-flask==0.61b0.dev"
    
    装饰器 @_syscall 的作用：
    - 统一处理 SubprocessError 异常
    - 将底层的子进程错误转换为更友好的 RuntimeError
    - 提供详细的错误信息（包含命令和包名）
    
    实现细节分析：
    """
    # 显式指定升级策略，覆盖用户可能在 pip.conf 中配置的策略
    # 这样可以确保行为的一致性，不受用户环境配置影响
    try:
        check_call(
            [
                # 1. sys.executable: 使用当前运行的 Python 解释器
                #    - 确保安装到正确的 Python 环境（虚拟环境或系统环境）
                #    - 避免使用全局的 pip 命令，因为可能指向不同的 Python 版本
                sys.executable,
                
                # 2. "-m pip": 以模块方式运行 pip
                #    - 等价于 python -m pip，而不是直接调用 pip 命令
                #    - 更可靠，因为直接使用当前 Python 的 pip 模块
                "-m",
                "pip",
                
                # 3. "install": pip 的安装命令
                "install",
                
                # 4. "-U" 或 "--upgrade": 升级标志
                #    - 如果包已安装，则升级到指定版本
                #    - 如果包未安装，则直接安装
                "-U",
                
                # 5. "--upgrade-strategy only-if-needed": 保守的升级策略
                #    - 只在必要时升级依赖包
                #    - 不会主动升级所有依赖到最新版本
                #    - 避免破坏现有的依赖关系
                #    
                #    对比其他策略：
                #    - "eager": 会升级所有依赖到最新版本（激进，可能破坏环境）
                #    - "only-if-needed": 只升级不满足要求的依赖（保守，推荐）
                #    
                #    示例场景：
                #    假设要安装 flask-instrumentation，它依赖 opentelemetry-sdk>=1.0
                #    - 如果当前 sdk 是 1.5，满足要求，则不升级（only-if-needed）
                #    - 如果当前 sdk 是 0.9，不满足要求，则升级到 1.0+（only-if-needed）
                #    - eager 策略会直接升级到最新版本，可能导致其他包不兼容
                "--upgrade-strategy",
                "only-if-needed",
                
                # 6. package: 要安装的包
                #    - 可以是简单的包名: "requests"
                #    - 可以带版本约束: "requests>=2.0"
                #    - 可以是精确版本: "requests==2.28.0"
                package,
            ]
        )
        # check_call 函数说明：
        # - 执行命令并等待完成
        # - 如果命令返回非零退出码，抛出 CalledProcessError
        # - 会继承当前进程的 stdout/stderr，所以安装过程会直接显示在终端
        
    except CalledProcessError as error:
        # CalledProcessError: pip 命令执行失败时抛出
        # 可能的失败原因：
        # 1. 包不存在（PyPI 上找不到）
        # 2. 网络问题（无法连接 PyPI）
        # 3. 权限问题（无法写入 site-packages）
        # 4. 依赖冲突（无法解决依赖关系）
        # 5. 版本不存在（指定的版本号不存在）
        
        # 注意：这里只是打印错误，不会重新抛出异常
        # 这意味着即使某个包安装失败，程序也会继续安装其他包
        # 这是一个设计决策：部分失败不应该阻止其他包的安装
        print(error)
        
        # 装饰器 @_syscall 会捕获 SubprocessError（CalledProcessError 的父类）
        # 并将其转换为 RuntimeError，提供更详细的错误信息


def _pip_check(libraries):
    """
    检查已安装的插件是否存在依赖冲突
    
    核心功能：
    1. 使用 pip check 命令检测依赖冲突
    2. 只关注 OpenTelemetry 相关的包，避免误报
    3. 发现冲突时抛出异常，阻止继续执行
    
    参数说明：
    - libraries: 库列表，格式为 [{"library": "flask>=1.0", "instrumentation": "opentelemetry-instrumentation-flask==0.61b0.dev"}, ...]
                 用于提取包名，检查是否存在于 pip check 的输出中
    
    为什么需要这个函数？
    - 自动安装多个插件时，可能会引入依赖冲突
    - 例如：插件 A 要求 sdk>=1.0，插件 B 要求 sdk<1.0
    - 及早发现冲突，避免运行时出现难以调试的问题
    
    pip check 命令说明：
    - 检查当前环境中所有包的依赖关系
    - 输出格式示例：
      成功: "No broken requirements found."
      失败: "opentelemetry-instrumentation-flask 1.0.1 has requirement opentelemetry-sdk<2.0,>=1.0, but you have opentelemetry-sdk 0.5."
    
    实现细节分析：
    """
    # 使用 Popen 而不是 check_call 的原因：
    # - 需要捕获 stdout 输出进行分析
    # - check_call 只能判断成功/失败，无法获取输出内容
    # - Popen 提供更细粒度的控制
    with Popen(
        [
            # 1. sys.executable: 使用当前 Python 解释器
            #    - 确保检查的是当前环境的依赖
            sys.executable,
            
            # 2. "-m pip check": 以模块方式运行 pip check
            #    - pip check 命令会验证所有已安装包的依赖关系
            #    - 检查是否有包的依赖要求未被满足
            "-m",
            "pip",
            "check"
        ],
        # stdout=PIPE: 将标准输出重定向到管道
        # - 这样可以通过 communicate() 方法读取输出
        # - 不会直接打印到终端
        stdout=PIPE
    ) as check_pipe:
        # communicate() 方法说明：
        # - 等待进程完成
        # - 返回 (stdout_data, stderr_data) 元组
        # - [0] 获取 stdout 数据
        # - decode() 将字节转换为字符串（默认 UTF-8）
        pip_check = check_pipe.communicate()[0].decode()
        
        # 转换为小写，方便后续不区分大小写的匹配
        # 原因：包名可能有不同的大小写形式
        # 例如：OpenTelemetry-SDK vs opentelemetry-sdk
        pip_check_lower = pip_check.lower()
    
    # 为什么要遍历 libraries？
    # - pip check 会检查所有包，包括非 OpenTelemetry 的包
    # - 我们只关心 OpenTelemetry 相关的冲突
    # - 避免因为用户环境中其他包的冲突而报错（不是我们的责任）
    
    # 遍历所有库配置
    for package_tup in libraries:
        # package_tup 是什么？
        # - 从代码上下文看，这里的命名可能有误导性
        # - 实际上 libraries 是字典列表，不是元组
        # - 这里应该是 package_dict，包含 "library" 和 "instrumentation" 键
        
        # 遍历包元组中的每个包
        # 注意：这里的逻辑有点奇怪，因为 package_tup 实际上是字典
        # 遍历字典会得到键名（"library", "instrumentation"）
        for package in package_tup:
            # package 是字典的键名，例如 "library" 或 "instrumentation"
            # package_tup[package] 是对应的值
            # 例如：package_tup["library"] = "flask >= 1.0"
            #      package_tup["instrumentation"] = "opentelemetry-instrumentation-flask==0.61b0.dev"
            
            # 检查包名是否出现在 pip check 的输出中
            # 转换为小写进行不区分大小写的匹配
            if package.lower() in pip_check_lower:
                # 发现冲突！
                # 抛出 RuntimeError，包含完整的 pip check 输出
                # 这会中断整个安装过程
                
                # 为什么要抛出异常而不是警告？
                # - 依赖冲突是严重问题，可能导致运行时错误
                # - 强制用户解决冲突，确保环境的一致性
                # - 避免安装后出现难以调试的问题
                raise RuntimeError(f"Dependency conflict found: {pip_check}")
    
    # 如果没有发现冲突，函数正常返回
    # 表示所有 OpenTelemetry 相关的包依赖关系都是正确的
    
    # 潜在问题分析：
    # 1. 这个检查逻辑可能不够精确
    #    - 只是简单的字符串匹配
    #    - 如果包名是另一个包名的子串，可能误报
    #    - 例如：检查 "flask"，但 pip check 输出中提到 "flask-login" 的冲突
    #
    # 2. 遍历逻辑有问题
    #    - for package in package_tup 会遍历字典的键（"library", "instrumentation"）
    #    - 应该是 for package in package_tup.values() 才对
    #    - 或者直接检查 package_tup["instrumentation"]
    #
    # 3. 性能考虑
    #    - 每次安装后都要运行 pip check，可能比较慢
    #    - 但为了确保环境一致性，这个开销是值得的
    
    # 改进建议：
    # 1. 使用正则表达式进行更精确的匹配
    # 2. 只检查 instrumentation 包，不检查 library 包
    # 3. 解析 pip check 的输出，提取具体的冲突信息


def _is_installed(req):
    """
    检查指定的库是否已安装且版本符合要求
    
    核心功能：
    1. 检查库是否已安装
    2. 检查已安装的版本是否满足版本约束
    
    参数：
        req: 库的依赖规范字符串，例如：
             - "flask >= 1.0"  (版本范围)
             - "requests ~= 2.0"  (兼容版本)
             - "django"  (任意版本)
    
    返回：
        bool: True 表示库已安装且版本符合要求，False 表示未安装或版本不符合
    
    工作流程：
    1. 解析依赖规范 -> Requirement 对象（包含库名和版本约束）
    2. 查询系统中该库的实际安装版本
    3. 验证实际版本是否满足版本约束
    
    设计要点：
    - 使用 packaging.requirements.Requirement 解析依赖规范
    - 使用 importlib.metadata.version 获取实际安装版本
    - 使用 specifier.filter() 进行版本匹配验证
    """
    # 将字符串解析为 Requirement 对象
    # Requirement 对象包含：
    #   - name: 库名（如 "flask"）
    #   - specifier: 版本约束（如 SpecifierSet(">=1.0")）
    req = Requirement(req)

    # 尝试获取该库的实际安装版本
    try:
        # version() 函数查询 Python 环境中已安装包的版本
        # 例如：version("flask") 可能返回 "2.0.1"
        dist_version = version(req.name)
    except PackageNotFoundError:
        # 库未安装，直接返回 False
        # 这是正常情况，不需要警告（用户可能确实没安装该库）
        return False

    # 验证实际版本是否满足版本约束
    # specifier.filter() 的工作原理：
    #   - 输入一个版本号，返回满足约束的版本列表
    #   - 如果返回空列表（False），说明版本不匹配
    # 
    # 示例：
    #   req.specifier = SpecifierSet(">=2.0")
    #   dist_version = "1.5.0"
    #   filter("1.5.0") 返回 [] (空列表，布尔值为 False)
    if not req.specifier.filter(dist_version):
        # 版本不匹配时记录警告
        # 这种情况说明：
        #   - 用户安装了该库，但版本太老或太新
        #   - OpenTelemetry 有对应的插件，但不支持当前版本
        #   - 跳过该库的自动埋点，避免兼容性问题
        logger.warning(
            "instrumentation for package %s is available"
            " but version %s is installed. Skipping.",
            req,  # 打印完整的依赖规范，如 "flask>=1.0"
            dist_version,  # 打印实际安装的版本，如 "0.9.0"
        )
        return False
    
    # 库已安装且版本符合要求
    return True


def _find_installed_libraries(default_instrumentations, libraries):
    for lib in default_instrumentations:
        yield lib

    for lib in libraries:
        if _is_installed(lib["library"]):
            yield lib["instrumentation"]


def _run_requirements(default_instrumentations, libraries):
    logger.setLevel(logging.ERROR)
    print(
        "\n".join(
            _find_installed_libraries(default_instrumentations, libraries)
        )
    )


def _run_install(default_instrumentations, libraries):
    for lib in _find_installed_libraries(default_instrumentations, libraries):
        _sys_pip_install(lib)
    _pip_check(libraries)


def run(
    default_instrumentations: Optional[list] = None,
    libraries: Optional[list] = None,
) -> None:
    action_install = "install"
    action_requirements = "requirements"

    parser = argparse.ArgumentParser(
        description="""
        opentelemetry-bootstrap detects installed libraries and automatically
        installs the relevant instrumentation packages for them.
        """
    )
    parser.add_argument(
        "--version",
        help="print version information",
        action="version",
        version="%(prog)s " + __version__,
    )
    parser.add_argument(
        "-a",
        "--action",
        choices=[action_install, action_requirements],
        default=action_requirements,
        help="""
        install - uses pip to install the new requirements using to the
                  currently active site-package.
        requirements - prints out the new requirements to stdout. Action can
                       be piped and appended to a requirements.txt file.
        """,
    )
    args = parser.parse_args()

    if libraries is None:
        libraries = gen_libraries

    if default_instrumentations is None:
        default_instrumentations = gen_default_instrumentations

    cmd = {
        action_install: _run_install,
        action_requirements: _run_requirements,
    }[args.action]
    cmd(default_instrumentations, libraries)
