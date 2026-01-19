#!/usr/bin/env python3
"""
环境变量模块注册机制演示脚本

功能：
1. 列出所有已注册的环境变量模块
2. 显示每个模块中定义的环境变量
3. 演示如何加载和使用这些模块
"""

from opentelemetry.util._importlib_metadata import entry_points
from re import sub


def print_separator(char="=", length=80):
    """打印分隔线"""
    print(char * length)


def print_section_title(title):
    """打印章节标题"""
    print_separator()
    print(f"  {title}")
    print_separator()
    print()


def list_all_environment_variable_modules():
    """列出所有已注册的环境变量模块"""
    print_section_title("📦 已注册的环境变量模块")
    
    all_env_vars = {}
    module_count = 0
    total_env_vars = 0
    
    for entry_point in entry_points(group="opentelemetry_environment_variables"):
        module_count += 1
        print(f"🔹 Entry Point #{module_count}")
        print(f"   名称: {entry_point.name}")
        print(f"   模块路径: {entry_point.value}")
        
        try:
            # 加载模块
            module = entry_point.load()
            print(f"   ✅ 模块加载成功")
            
            # 查找所有 OTEL_ 开头的常量
            env_vars = []
            for attr in dir(module):
                if attr.startswith("OTEL_"):
                    value = getattr(module, attr)
                    env_vars.append((attr, value))
                    all_env_vars[attr] = {
                        "value": value,
                        "module": entry_point.value,
                        "entry_point": entry_point.name
                    }
            
            # 显示环境变量
            print(f"   环境变量列表:")
            for env_var, value in sorted(env_vars):
                print(f"     • {env_var}")
                # 如果有文档字符串，显示它
                if hasattr(module, env_var):
                    obj = getattr(module, env_var)
                    if isinstance(obj, str) and obj == env_var:
                        # 这是一个环境变量常量
                        pass
            
            print(f"   📊 总计: {len(env_vars)} 个环境变量")
            total_env_vars += len(env_vars)
            
        except Exception as e:
            print(f"   ❌ 加载失败: {e}")
        
        print()
    
    print_separator("-")
    print(f"📊 统计信息:")
    print(f"   • 环境变量模块数量: {module_count}")
    print(f"   • 环境变量总数: {total_env_vars}")
    print_separator("-")
    print()
    
    return all_env_vars


def demonstrate_command_line_argument_generation(all_env_vars):
    """演示命令行参数生成过程"""
    print_section_title("🔧 命令行参数生成演示")
    
    print("这是 opentelemetry-instrument 如何将环境变量转换为命令行参数的过程：\n")
    
    # 模拟 run() 函数中的转换逻辑
    argument_mapping = {}
    
    for env_var, info in sorted(all_env_vars.items()):
        # 转换环境变量名为命令行参数名
        # 移除 OTEL_ 或 OTEL_PYTHON_ 前缀，转换为小写
        argument = sub(r"OTEL_(PYTHON_)?", "", env_var).lower()
        
        argument_mapping[argument] = env_var
        
        print(f"环境变量: {env_var}")
        print(f"  ↓ 转换规则: 移除 'OTEL_' 或 'OTEL_PYTHON_' 前缀，转换为小写")
        print(f"命令行参数: --{argument}")
        print(f"  来源模块: {info['module']}")
        print()
    
    print_separator("-")
    print(f"📊 生成了 {len(argument_mapping)} 个命令行参数")
    print_separator("-")
    print()
    
    return argument_mapping


def demonstrate_usage_examples(argument_mapping):
    """演示使用示例"""
    print_section_title("💡 使用示例")
    
    # 选择一些常用的参数作为示例
    common_args = [
        ("service_name", "my-flask-app"),
        ("traces_exporter", "console"),
        ("metrics_exporter", "prometheus"),
        ("exporter_otlp_endpoint", "http://localhost:4317"),
        ("disabled_instrumentations", "flask,requests"),
    ]
    
    print("示例 1: 基本使用")
    print("-" * 80)
    cmd_parts = ["opentelemetry-instrument"]
    for arg, value in common_args[:3]:
        if arg in argument_mapping:
            cmd_parts.append(f"--{arg}={value}")
    cmd_parts.append("python app.py")
    print(" \\\n  ".join(cmd_parts))
    print()
    
    print("这会设置以下环境变量:")
    for arg, value in common_args[:3]:
        if arg in argument_mapping:
            env_var = argument_mapping[arg]
            print(f"  {env_var}={value}")
    print()
    
    print("示例 2: 完整配置")
    print("-" * 80)
    cmd_parts = ["opentelemetry-instrument"]
    for arg, value in common_args:
        if arg in argument_mapping:
            cmd_parts.append(f"--{arg}={value}")
    cmd_parts.append("python app.py --port 8080")
    print(" \\\n  ".join(cmd_parts))
    print()
    
    print("这会设置以下环境变量:")
    for arg, value in common_args:
        if arg in argument_mapping:
            env_var = argument_mapping[arg]
            print(f"  {env_var}={value}")
    print()


def demonstrate_entry_point_mechanism():
    """演示 Entry Point 机制"""
    print_section_title("🔌 Entry Point 机制演示")
    
    print("Entry Points 是 Python 的插件注册机制。")
    print("包可以通过 pyproject.toml 注册 Entry Points，其他代码可以在运行时发现它们。\n")
    
    print("注册方式（在 pyproject.toml 中）:")
    print("-" * 80)
    print("""
[project.entry-points.opentelemetry_environment_variables]
instrumentation = "opentelemetry.instrumentation.environment_variables"
sdk = "opentelemetry.sdk.environment_variables"
    """.strip())
    print()
    
    print("发现方式（在 Python 代码中）:")
    print("-" * 80)
    print("""
from opentelemetry.util._importlib_metadata import entry_points

# 查找所有环境变量模块
for entry_point in entry_points(group="opentelemetry_environment_variables"):
    print(f"发现: {entry_point.name} -> {entry_point.value}")
    
    # 加载模块
    module = entry_point.load()
    
    # 使用模块
    for attr in dir(module):
        if attr.startswith("OTEL_"):
            print(f"  - {attr}")
    """.strip())
    print()


def show_specific_module_details():
    """显示特定模块的详细信息"""
    print_section_title("🔍 模块详细信息")
    
    # 查找 instrumentation 模块
    for entry_point in entry_points(group="opentelemetry_environment_variables"):
        if entry_point.name == "instrumentation":
            print(f"📦 模块: {entry_point.value}")
            print()
            
            module = entry_point.load()
            
            print("定义的环境变量:")
            print("-" * 80)
            for attr in sorted(dir(module)):
                if attr.startswith("OTEL_"):
                    value = getattr(module, attr)
                    print(f"\n{attr} = \"{value}\"")
                    
                    # 尝试获取文档字符串
                    try:
                        # 获取模块的源代码来查找文档字符串
                        import inspect
                        source = inspect.getsource(module)
                        # 简单的文档字符串提取（实际实现可能更复杂）
                        if f'{attr} = ' in source:
                            lines = source.split('\n')
                            for i, line in enumerate(lines):
                                if f'{attr} = ' in line:
                                    # 查找后续的文档字符串
                                    if i + 1 < len(lines) and '"""' in lines[i + 1]:
                                        doc_start = i + 1
                                        doc_lines = []
                                        for j in range(doc_start, min(doc_start + 5, len(lines))):
                                            doc_lines.append(lines[j])
                                            if j > doc_start and '"""' in lines[j]:
                                                break
                                        if doc_lines:
                                            print(f"文档: {''.join(doc_lines).strip()}")
                    except:
                        pass
            
            print()
            break


def main():
    """主函数"""
    print()
    print("=" * 80)
    print("  OpenTelemetry 环境变量模块注册机制演示")
    print("=" * 80)
    print()
    
    # 1. 列出所有环境变量模块
    all_env_vars = list_all_environment_variable_modules()
    
    # 2. 演示 Entry Point 机制
    demonstrate_entry_point_mechanism()
    
    # 3. 演示命令行参数生成
    argument_mapping = demonstrate_command_line_argument_generation(all_env_vars)
    
    # 4. 演示使用示例
    demonstrate_usage_examples(argument_mapping)
    
    # 5. 显示特定模块的详细信息
    show_specific_module_details()
    
    print_section_title("✅ 演示完成")
    print("💡 提示:")
    print("   • 环境变量模块通过 Entry Points 机制注册")
    print("   • opentelemetry-instrument 自动发现所有环境变量模块")
    print("   • 每个环境变量自动生成对应的命令行参数")
    print("   • 命令行参数会被转换为环境变量传递给目标程序")
    print()
    print("📚 相关文档:")
    print("   • 环境变量模块注册机制详解.md")
    print("   • run函数执行流程详解.md")
    print()


if __name__ == "__main__":
    main()
