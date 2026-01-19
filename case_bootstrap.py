#!/usr/bin/env python3
"""
OpenTelemetry Bootstrap 交互式调试工具

这个脚本提供了一个交互式菜单，让你可以方便地调试 bootstrap 的各种功能。
你可以在任何地方设置断点，然后通过菜单选择要执行的操作。

用法：
    python case_bootstrap.py
    
然后通过交互式菜单选择要执行的操作。
"""

import sys
import logging
from pathlib import Path

# 添加 opentelemetry-instrumentation 到 Python 路径
instrumentation_path = Path(__file__).parent / "opentelemetry-instrumentation" / "src"
sys.path.insert(0, str(instrumentation_path))

from opentelemetry.instrumentation.bootstrap import (
    run,
    _is_installed,
    _find_installed_libraries,
)
from opentelemetry.instrumentation.bootstrap_gen import (
    default_instrumentations,
    libraries,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title=""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def print_menu():
    """打印主菜单"""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "OpenTelemetry Bootstrap 调试菜单" + " " * 26 + "║")
    print("╠" + "═" * 78 + "╣")
    print("║  1. 预览将要安装的插件（基于当前环境）                                    ║")
    print("║  2. 查看所有支持的库列表                                                  ║")
    print("║  3. 调试特定库的检测逻辑（交互式输入）                                    ║")
    print("║  4. 测试自定义库列表                                                      ║")
    print("║  5. 生成 requirements.txt（不安装）                                       ║")
    print("║  6. 实际执行安装（⚠️  会执行 pip install）                                ║")
    print("║  7. 查看默认插件列表                                                      ║")
    print("║  8. 调试 run() 函数（⭐ 设置断点后选择此项）                              ║")
    print("║  0. 退出                                                                  ║")
    print("╚" + "═" * 78 + "╝")


def debug_library_detection(library_name=None):
    """调试库的检测逻辑"""
    print_separator("库检测调试")
    
    if library_name is None:
        # 交互式输入
        print("💡 常用的库:")
        common_libs = ["flask", "requests", "django", "psycopg2", "redis", "mysql", "sqlalchemy"]
        for lib in common_libs:
            print(f"  - {lib}")
        
        print("\n请输入要调试的库名称（或按 Enter 查看所有已安装的库）:")
        library_name = input(">>> ").strip().lower()
    
    if library_name:
        # 检测特定库
        print(f"\n🔍 检测库: {library_name}\n")
        
        found = False
        for lib in libraries:
            lib_name = lib["library"].split()[0].lower()
            if library_name in lib_name:
                found = True
                print(f"📋 库配置信息:")
                print(f"  - 库名称: {lib_name}")
                print(f"  - 版本要求: {lib['library']}")
                print(f"  - 插件名称: {lib['instrumentation']}")
                
                is_installed = _is_installed(lib["library"])
                print(f"\n🔍 检测结果:")
                if is_installed:
                    print(f"  ✅ 已安装: {lib_name}")
                    print(f"  ✅ 将会安装插件: {lib['instrumentation']}")
                else:
                    print(f"  ❌ 未安装: {lib_name}")
                    print(f"  💡 提示: 安装后才会自动安装对应的插件")
                print()
        
        if not found:
            print(f"❌ 未找到库 '{library_name}' 的映射关系")
            print(f"💡 提示: 使用菜单选项 2 查看所有支持的库")
    else:
        # 检测所有已安装的库
        print("\n🔍 检测所有已安装的库:\n")
        
        print("📋 默认插件（无条件安装）:")
        for idx, instr in enumerate(default_instrumentations, 1):
            print(f"  {idx}. {instr}")
        
        print(f"\n📋 条件插件（根据已安装的库）:")
        installed_count = 0
        for lib in libraries:
            if _is_installed(lib["library"]):
                installed_count += 1
                print(f"  ✅ {lib['library']}")
                print(f"     → {lib['instrumentation']}")
        
        if installed_count == 0:
            print("  ❌ 没有找到已安装的支持库")
        
        print(f"\n📊 统计:")
        print(f"  - 默认插件: {len(default_instrumentations)} 个")
        print(f"  - 条件插件（已安装）: {installed_count} 个")
        print(f"  - 总计: {len(default_instrumentations) + installed_count} 个")


def list_all_supported_libraries():
    """列出所有支持的库"""
    print_separator("所有支持的库")
    
    print(f"📚 OpenTelemetry 支持 {len(libraries)} 个库的自动埋点:\n")
    
    # 按字母顺序排序
    sorted_libs = sorted(libraries, key=lambda x: x["library"].lower())
    
    for i, lib in enumerate(sorted_libs, 1):
        lib_name = lib["library"].split()[0]
        version_constraint = lib["library"][len(lib_name):].strip()
        is_installed = _is_installed(lib["library"])
        status = "✅" if is_installed else "❌"
        
        print(f"{i:3d}. {status} {lib_name:30s} {version_constraint:20s}")
        print(f"      → {lib['instrumentation']}")
        
        if i % 10 == 0 and i < len(sorted_libs):
            print()  # 每10个库添加一个空行，便于阅读


def demo_custom_libraries():
    """演示自定义的库列表"""
    print_separator("测试自定义库列表")
    
    print("请输入要测试的库列表（用逗号分隔，例如: flask, requests, django）:")
    input_libs = input(">>> ").strip()
    
    if not input_libs:
        print("❌ 库列表不能为空")
        return
    
    # 解析输入
    test_libs = [lib.strip().lower() for lib in input_libs.split(",")]
    
    print(f"\n🧪 测试库列表: {', '.join(test_libs)}\n")
    
    # 检查每个库
    found = []
    not_found = []
    
    for test_lib in test_libs:
        matched = False
        for lib in libraries:
            lib_name = lib["library"].split()[0].lower()
            if test_lib in lib_name:
                matched = True
                instr_name = lib["instrumentation"]
                found.append(instr_name)
                print(f"  ✅ {test_lib:20s} → {instr_name}")
                break
        
        if not matched:
            not_found.append(test_lib)
            print(f"  ❌ {test_lib:20s} → 不支持")
    
    print(f"\n📊 统计:")
    print(f"  - 支持的库: {len(found)}")
    print(f"  - 不支持的库: {len(not_found)}")
    
    if found:
        print(f"\n📦 将安装的插件:")
        for pkg in found:
            print(f"  - {pkg}")
    
    print("\n💡 提示: 这是一个测试预览，不会实际安装任何包")


def show_install_preview():
    """预览将要安装的插件"""
    print_separator("安装预览")
    
    print("🔍 正在检测当前环境中已安装的库...\n")
    
    plugins = list(_find_installed_libraries(default_instrumentations, libraries))
    
    if plugins:
        print(f"📦 将要安装的插件（共 {len(plugins)} 个）:\n")
        for idx, plugin in enumerate(plugins, 1):
            print(f"  {idx}. {plugin}")
    else:
        print("❌ 没有找到需要安装的插件")
        print("💡 提示: 请先安装一些支持的库，如 flask, requests, django 等")
    
    print("\n⚠️  注意: 这只是预览，不会实际安装")
    print("💡 提示: 使用菜单选项 6 来实际安装")


def generate_requirements():
    """生成 requirements.txt"""
    print_separator("生成 requirements.txt")
    
    print("🔄 正在生成 requirements.txt...\n")
    
    # 调用 run 函数，action 为 requirements
    original_argv = sys.argv
    sys.argv = ["bootstrap", "-a", "requirements"]
    
    try:
        run()
        print("\n✅ requirements.txt 生成完成")
    except SystemExit:
        pass
    finally:
        sys.argv = original_argv


def actual_install():
    """实际执行安装"""
    print_separator("⚠️  实际执行安装")
    
    print("⚠️  警告: 这将会执行 pip install 命令，实际安装插件到你的环境中！")
    print("\n确定要继续吗？(yes/no):")
    
    confirm = input(">>> ").strip().lower()
    
    if confirm not in ["yes", "y"]:
        print("❌ 已取消安装")
        return
    
    print("\n🔄 正在安装插件...\n")
    
    # 调用 run 函数，action 为 install
    original_argv = sys.argv
    sys.argv = ["bootstrap", "-a", "install"]
    
    try:
        run()
        print("\n✅ 安装完成")
    except SystemExit:
        pass
    finally:
        sys.argv = original_argv


def show_default_instrumentations():
    """显示默认插件列表"""
    print_separator("默认插件列表")
    
    print(f"📦 共有 {len(default_instrumentations)} 个默认插件（无条件安装）:\n")
    
    for i, instr in enumerate(default_instrumentations, 1):
        print(f"{i:3d}. {instr}")
    
    print("\n💡 提示: 这些插件会无条件安装，不需要检测对应的库")


def debug_run_function():
    """调试 run() 函数 - 在这里设置断点"""
    print_separator("调试 run() 函数")
    
    print("💡 提示: 在下面的 run() 调用处设置断点，然后选择此菜单项")
    print("🔍 即将调用 run() 函数...\n")
    
    print("请选择要执行的操作:")
    print("  1. requirements - 生成 requirements.txt")
    print("  2. install - 实际安装插件")
    print("  3. 自定义参数")
    
    choice = input(">>> ").strip()
    
    if choice == "1":
        sys.argv = ["bootstrap", "-a", "requirements"]
    elif choice == "2":
        sys.argv = ["bootstrap", "-a", "install"]
    elif choice == "3":
        print("请输入完整的命令行参数（例如: -a requirements）:")
        args = input(">>> ").strip()
        sys.argv = ["bootstrap"] + args.split()
    else:
        print("❌ 无效的选择")
        return
    
    print(f"\n🚀 执行命令: {' '.join(sys.argv)}\n")
    print("=" * 80)
    print("⬇️  在下面这行设置断点，然后按 F8 单步调试 ⬇️")
    print("=" * 80)
    
    # 🔴 在这里设置断点！
    try:
        run()  # ← 在这里设置断点，然后 F7 进入函数内部调试
    except SystemExit:
        pass
    
    print("\n✅ run() 函数执行完成")


def main():
    """主函数 - 交互式菜单"""
    print("\n" + "🎯" * 40)
    print("  OpenTelemetry Bootstrap 交互式调试工具")
    print("  💡 提示: 你可以在任何函数中设置断点，然后通过菜单触发执行")
    print("🎯" * 40)
    
    while True:
        print_menu()
        
        choice = input("\n请选择操作 (0-8): ").strip()
        
        try:
            if choice == "0":
                print("\n👋 再见！")
                break
            elif choice == "1":
                show_install_preview()
            elif choice == "2":
                list_all_supported_libraries()
            elif choice == "3":
                debug_library_detection()
            elif choice == "4":
                demo_custom_libraries()
            elif choice == "5":
                generate_requirements()
            elif choice == "6":
                actual_install()
            elif choice == "7":
                show_default_instrumentations()
            elif choice == "8":
                debug_run_function()
            else:
                print("❌ 无效的选择，请输入 0-8")
        
        except KeyboardInterrupt:
            print("\n\n⚠️  操作已中断")
        except Exception as e:
            logger.error(f"❌ 错误: {e}", exc_info=True)
        
        input("\n按 Enter 继续...")


if __name__ == "__main__":
    main()
