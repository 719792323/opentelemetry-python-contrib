#!/usr/bin/env python3
"""
OpenTelemetry Auto Instrumentation Run 函数调试脚本

功能：
1. 模拟 opentelemetry-instrument 命令的执行
2. 支持断点调试 run() 函数
3. 提供多种测试场景

使用方法：
1. 在 PyCharm 中打开此文件
2. 在 run() 函数内部设置断点（推荐位置已标注）
3. 右键选择 "Debug 'debug_auto_instrumentation'"
4. 选择要测试的场景

断点建议位置：
- 第 45 行：run() 函数入口
- 第 75 行：参数解析完成后
- 第 85 行：环境变量设置后
- 第 110 行：PYTHONPATH 设置后
- 第 113 行：execl 执行前（最关键）
"""

import sys
import os
from pathlib import Path

# 添加项目路径到 sys.path
project_root = Path(__file__).parent
instrumentation_path = project_root / "opentelemetry-instrumentation" / "src"
sys.path.insert(0, str(instrumentation_path))


def case_run_with_flask_app():
    """
    测试场景 1：运行一个 Flask 应用
    
    模拟命令：
    opentelemetry-instrument --service_name=my-flask-app python app.py
    """
    print("=" * 80)
    print("测试场景 1：Flask 应用自动埋点")
    print("=" * 80)
    
    # 模拟命令行参数
    sys.argv = [
        "opentelemetry-instrument",
        "--service_name=my-flask-app",
        "--traces_exporter=console",
        "--metrics_exporter=console",
        "python",
        "-c",
        "print('Hello from Flask app')"
    ]
    
    print(f"\n📋 模拟的命令行参数:")
    print(f"   {' '.join(sys.argv)}\n")
    
    # 导入并调用 run 函数
    from opentelemetry.instrumentation.auto_instrumentation import run
    
    print("🚀 开始执行 run() 函数...")
    print("💡 提示：在 run() 函数内设置断点进行调试\n")
    
    # ⚠️ 重要断点位置：在这里设置断点，然后单步进入 run() 函数
    run()


def case_run_with_django_app():
    """
    测试场景 2：运行一个 Django 应用
    
    模拟命令：
    opentelemetry-instrument --service_name=my-django-app python manage.py runserver
    """
    print("=" * 80)
    print("测试场景 2：Django 应用自动埋点")
    print("=" * 80)
    
    sys.argv = [
        "opentelemetry-instrument",
        "--service_name=my-django-app",
        "--traces_exporter=otlp",
        "--exporter_otlp_endpoint=http://localhost:4317",
        "python",
        "manage.py",
        "runserver"
    ]
    
    print(f"\n📋 模拟的命令行参数:")
    print(f"   {' '.join(sys.argv)}\n")
    
    from opentelemetry.instrumentation.auto_instrumentation import run
    
    print("🚀 开始执行 run() 函数...")
    print("💡 提示：在 run() 函数内设置断点进行调试\n")
    
    # ⚠️ 重要断点位置
    run()


def case_run_with_custom_script():
    """
    测试场景 3：运行自定义 Python 脚本
    
    模拟命令：
    opentelemetry-instrument python my_script.py --arg1 value1
    """
    print("=" * 80)
    print("测试场景 3：自定义脚本自动埋点")
    print("=" * 80)
    
    sys.argv = [
        "opentelemetry-instrument",
        "python",
        "-c",
        "import time; print('Script running...'); time.sleep(0.1); print('Done!')"
    ]
    
    print(f"\n📋 模拟的命令行参数:")
    print(f"   {' '.join(sys.argv)}\n")
    
    from opentelemetry.instrumentation.auto_instrumentation import run
    
    print("🚀 开始执行 run() 函数...")
    print("💡 提示：在 run() 函数内设置断点进行调试\n")
    
    # ⚠️ 重要断点位置
    run()


def case_run_with_environment_variables():
    """
    测试场景 4：测试环境变量的处理
    
    模拟命令：
    OTEL_SERVICE_NAME=my-service opentelemetry-instrument python app.py
    """
    print("=" * 80)
    print("测试场景 4：环境变量处理测试")
    print("=" * 80)
    
    # 设置环境变量
    os.environ["OTEL_SERVICE_NAME"] = "my-service-from-env"
    os.environ["OTEL_TRACES_EXPORTER"] = "console"
    
    sys.argv = [
        "opentelemetry-instrument",
        "--service_name=my-service-from-arg",  # 这个会覆盖环境变量
        "python",
        "-c",
        "import os; print(f'Service Name: {os.environ.get(\"OTEL_SERVICE_NAME\")}')"
    ]
    
    print(f"\n📋 环境变量:")
    print(f"   OTEL_SERVICE_NAME={os.environ.get('OTEL_SERVICE_NAME')}")
    print(f"   OTEL_TRACES_EXPORTER={os.environ.get('OTEL_TRACES_EXPORTER')}")
    
    print(f"\n📋 命令行参数:")
    print(f"   {' '.join(sys.argv)}\n")
    
    from opentelemetry.instrumentation.auto_instrumentation import run
    
    print("🚀 开始执行 run() 函数...")
    print("💡 提示：观察命令行参数如何覆盖环境变量\n")
    
    # ⚠️ 重要断点位置
    run()


def case_run_step_by_step():
    """
    测试场景 5：逐步调试模式（推荐用于学习）
    
    这个场景会在关键位置打印调试信息，帮助理解 run() 函数的执行流程
    """
    print("=" * 80)
    print("测试场景 5：逐步调试模式")
    print("=" * 80)
    print("\n📚 run() 函数执行流程：")
    print("   1. 创建 ArgumentParser")
    print("   2. 动态添加 OTEL 环境变量对应的参数")
    print("   3. 解析命令行参数")
    print("   4. 将参数值设置到环境变量")
    print("   5. 处理 PYTHONPATH")
    print("   6. 使用 execl 替换当前进程执行目标命令")
    print("\n💡 建议断点位置：")
    print("   - run() 函数入口")
    print("   - args = parser.parse_args() 之后")
    print("   - environ[otel_environment_variable] = value 处")
    print("   - execl(executable, executable, *args.command_args) 之前")
    print()
    
    sys.argv = [
        "opentelemetry-instrument",
        "--service_name=debug-test",
        "--traces_exporter=console",
        "python",
        "-c",
        "print('Hello, OpenTelemetry!')"
    ]
    
    print(f"📋 测试命令:")
    print(f"   {' '.join(sys.argv)}\n")
    
    from opentelemetry.instrumentation.auto_instrumentation import run
    
    print("🚀 开始执行 run() 函数...")
    print("⚠️  在下一行设置断点，然后单步调试！\n")
    
    # ⚠️⚠️⚠️ 最重要的断点位置：在这里设置断点！⚠️⚠️⚠️
    run()


def interactive_menu():
    """
    交互式菜单
    """
    print("\n" + "=" * 80)
    print("OpenTelemetry Auto Instrumentation Run 函数调试工具")
    print("=" * 80)
    print("\n请选择测试场景：")
    print("  1. Flask 应用自动埋点")
    print("  2. Django 应用自动埋点")
    print("  3. 自定义脚本自动埋点")
    print("  4. 环境变量处理测试")
    print("  5. 逐步调试模式（推荐）")
    print("  0. 退出")
    print()
    
    choice = input("请输入选项 (0-5): ").strip()
    
    scenarios = {
        "1": case_run_with_flask_app,
        "2": case_run_with_django_app,
        "3": case_run_with_custom_script,
        "4": case_run_with_environment_variables,
        "5": case_run_step_by_step,
    }
    
    if choice == "0":
        print("\n👋 再见！")
        return
    
    if choice in scenarios:
        print()
        try:
            scenarios[choice]()
        except SystemExit as e:
            print(f"\n✅ run() 函数执行完成（SystemExit: {e.code}）")
        except Exception as e:
            print(f"\n❌ 执行出错: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ 无效的选项，请重新选择")
        interactive_menu()


def main():
    """
    主函数
    
    使用方式：
    1. 直接运行：python debug_auto_instrumentation.py
    2. PyCharm 调试：右键 -> Debug 'debug_auto_instrumentation'
    """
    print("\n" + "🔧" * 40)
    print("OpenTelemetry Auto Instrumentation 调试工具")
    print("🔧" * 40)
    
    # 检查是否在调试模式
    if sys.gettrace() is not None:
        print("\n✅ 检测到调试模式")
        print("💡 提示：")
        print("   1. 打开 auto_instrumentation/__init__.py")
        print("   2. 在 run() 函数内设置断点")
        print("   3. 继续执行，断点会自动触发")
        print()
    else:
        print("\n⚠️  当前不在调试模式")
        print("💡 建议：在 PyCharm 中右键选择 'Debug' 运行此脚本")
        print()
    
    # 显示交互式菜单
    interactive_menu()


if __name__ == "__main__":
    main()
