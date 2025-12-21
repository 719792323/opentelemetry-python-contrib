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
模拟的 mycache 库 - 用于测试和演示
==============================================================================

这个文件模拟了一个简单的缓存客户端库，用于演示 Instrumentation 如何工作。

【说明】
在实际场景中，mycache 是一个第三方库（如 redis、memcached 等）
这里我们创建一个简单的内存缓存来模拟
"""

from typing import Any, Optional

__version__ = "1.0.0"


class CacheClient:
    """
    同步缓存客户端
    
    这是我们要埋点的目标类
    
    【与 Java 对比】
    Java 中这相当于：
    ```java
    public class CacheClient {
        public Object get(String key) { ... }
        public void set(String key, Object value) { ... }
        public void delete(String key) { ... }
    }
    ```
    """
    
    def __init__(self, host: str = "localhost", port: int = 11211, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self._cache: dict[str, Any] = {}
        print(f"[mycache] CacheClient 创建: {host}:{port} db={db}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        这个方法会被 Instrumentation 包装
        包装后的调用流程：
        1. 创建 Span
        2. 设置属性（db.system, db.statement 等）
        3. 调用原始的 get 方法
        4. 记录结果
        5. 结束 Span
        """
        print(f"[mycache] GET {key}")
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 0) -> bool:
        """设置缓存值"""
        print(f"[mycache] SET {key} = {value} (ttl={ttl})")
        self._cache[key] = value
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        print(f"[mycache] DELETE {key}")
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def mget(self, *keys: str) -> list:
        """批量获取"""
        print(f"[mycache] MGET {keys}")
        return [self._cache.get(k) for k in keys]


# 模拟异步客户端子模块
class asyncio:
    """模拟 mycache.asyncio 子模块"""
    
    class AsyncCacheClient:
        """
        异步缓存客户端
        
        【与 Java 对比】
        Java 中这可能是：
        ```java
        public class AsyncCacheClient {
            public CompletableFuture<Object> getAsync(String key) { ... }
        }
        ```
        """
        
        def __init__(self, host: str = "localhost", port: int = 11211, db: int = 0):
            self.host = host
            self.port = port
            self.db = db
            self._cache: dict[str, Any] = {}
            print(f"[mycache.asyncio] AsyncCacheClient 创建: {host}:{port}")
        
        async def get(self, key: str) -> Optional[Any]:
            """异步获取"""
            print(f"[mycache.asyncio] GET {key}")
            return self._cache.get(key)
        
        async def set(self, key: str, value: Any, ttl: int = 0) -> bool:
            """异步设置"""
            print(f"[mycache.asyncio] SET {key} = {value}")
            self._cache[key] = value
            return True
