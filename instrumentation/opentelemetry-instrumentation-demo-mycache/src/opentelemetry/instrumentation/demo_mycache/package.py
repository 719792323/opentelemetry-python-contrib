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

# =============================================================================
# package.py - 目标库依赖声明
# =============================================================================
#
# 【作用】
# 此文件声明 Instrumentor 依赖的目标库版本
# 在 instrumentation_dependencies() 方法中返回此变量
#
# 【与 Java 对比】
# Java:
#   @Override
#   public ElementMatcher<ClassLoader> classLoaderOptimization() {
#     return hasClassesNamed("com.example.mycache.CacheClient");
#   }
#   
#   或者在 TypeInstrumentation 中：
#   @Override  
#   public ElementMatcher<TypeDescription> typeMatcher() {
#     return named("com.example.mycache.CacheClient");
#   }
#
# Python:
#   def instrumentation_dependencies(self) -> Collection[str]:
#       return _instruments  # 返回下面定义的元组
#
# 【检测流程】
# 1. BaseInstrumentor.instrument() 调用 _check_dependency_conflicts()
# 2. 框架使用 packaging.requirements.Requirement 解析版本约束
# 3. 使用 importlib.metadata.version() 获取已安装版本
# 4. 比较版本是否满足约束

_instruments = ("mycache >= 1.0",)

# 【扩展】如果支持多个版本分支，可以这样写：
# _instruments = (
#     "mycache >= 1.0, < 3.0",  # 支持 1.x 和 2.x
# )
#
# 如果需要 either/or 依赖（满足任一即可），使用 instruments-any：
# _instruments_any = ("mycache >= 1.0", "mycache-async >= 1.0")
