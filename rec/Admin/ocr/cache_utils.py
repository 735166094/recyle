import logging
import time
from functools import wraps
from typing import Any, Optional, Callable, Dict
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheMetrics:
    """缓存指标收集器"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_time = 0

    def record_hit(self, duration: float):
        self.hits += 1
        self.total_time += duration

    def record_miss(self, duration: float):
        self.misses += 1
        self.total_time += duration

    def record_error(self):
        self.errors += 1

    @property
    def total_operations(self):
        return self.hits + self.misses + self.errors

    @property
    def hit_rate(self):
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0

    @property
    def avg_response_time(self):
        total = self.hits + self.misses
        return self.total_time / total if total > 0 else 0


def cache_operation(cache_key: str, timeout: int = None,
                    local_ttl: int = 30, use_local_cache: bool = True):
    """缓存操作装饰器 - 修正版本"""

    def decorator(func):
        @wraps(func)
        def wrapper(cls, *args, **kwargs):
            start_time = time.time()

            # 检查缓存是否启用
            if not cls.is_cache_enabled():
                logger.debug("缓存已禁用，直接执行函数")
                return func(cls, *args, **kwargs)

            # 生成完整的缓存键
            key_parts = [cache_key]
            if args:
                key_parts.extend(str(arg) for arg in args)
            if kwargs:
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))

            full_key = ":".join(key_parts)
            timeout_val = timeout or cls.CACHE_TIMEOUTS.get(cache_key, 3600)

            # 先检查本地缓存
            if use_local_cache:
                local_cached = cls._get_local_cache(full_key)
                if local_cached is not None:
                    cls._metrics.record_hit(time.time() - start_time)
                    logger.debug(f"本地缓存命中: {full_key}")
                    return local_cached

            try:
                # 检查Redis缓存
                cached_result = cache.get(full_key)
                if cached_result is not None:
                    cls._metrics.record_hit(time.time() - start_time)
                    logger.debug(f"Redis缓存命中: {full_key}")

                    # 更新本地缓存
                    if use_local_cache:
                        cls._set_local_cache(full_key, cached_result, local_ttl)

                    return cached_result

                # 缓存未命中，执行函数
                cls._metrics.record_miss(time.time() - start_time)
                logger.debug(f"缓存未命中: {full_key}")

                result = func(cls, *args, **kwargs)

                # 缓存结果
                if result is not None:
                    cache.set(full_key, result, timeout_val)
                    if use_local_cache:
                        cls._set_local_cache(full_key, result, local_ttl)

                return result

            except Exception as e:
                cls._metrics.record_error()
                logger.error(f"缓存操作失败: {str(e)}")
                # 缓存失败时直接执行函数
                return func(cls, *args, **kwargs)

        return wrapper

    return decorator


class CacheManager:
    """缓存管理工具类 - 修正版本"""

    # 缓存键前缀
    CACHE_KEYS = {
        'huawei_config': 'ocr:cfg:hw',
        'ocr_interfaces': 'ocr:cfg:if',
        'certificate_types': 'ocr:cfg:ct',
        'user_records': 'ocr:u:{}:rec',
        'user_stats': 'ocr:u:{}:stat',
        'vin_config': 'ocr:cfg:vin',
        'vin_query': 'ocr:vin:{}',
    }

    # 缓存过期时间（秒）
    CACHE_TIMEOUTS = {
        'huawei_config': 7200,
        'ocr_interfaces': 7200,
        'certificate_types': 3600,
        'user_records': 600,
        'user_stats': 1200,
        'vin_config': 7200,
        'vin_query': 1800,
    }

    # 性能指标
    _metrics = CacheMetrics()

    # 本地内存缓存
    _local_cache = {}
    _local_cache_ttl = {}
    _cache_enabled = None

    @classmethod
    def is_cache_enabled(cls) -> bool:
        """检查缓存是否启用"""
        if cls._cache_enabled is None:
            cls._cache_enabled = getattr(settings, 'OCR_CACHE_ENABLED', True)
        return cls._cache_enabled

    @classmethod
    def _get_local_cache(cls, key: str) -> Any:
        """获取本地缓存"""
        if key in cls._local_cache_ttl:
            if time.time() > cls._local_cache_ttl[key]:
                del cls._local_cache[key]
                del cls._local_cache_ttl[key]
                return None
            return cls._local_cache.get(key)
        return None

    @classmethod
    def _set_local_cache(cls, key: str, value: Any, ttl: int = 60):
        """设置本地缓存"""
        cls._local_cache[key] = value
        cls._local_cache_ttl[key] = time.time() + ttl

        # 清理过期缓存
        if len(cls._local_cache) > 1000:
            current_time = time.time()
            expired_keys = [
                k for k, exp in cls._local_cache_ttl.items()
                if exp < current_time
            ]
            for k in expired_keys:
                del cls._local_cache[k]
                del cls._local_cache_ttl[k]

    @classmethod
    @cache_operation('huawei_config', use_local_cache=True)
    def get_huawei_config(cls) -> Optional[Dict]:
        """获取华为云配置缓存"""
        # 装饰器会自动处理缓存逻辑，这里返回None表示缓存未命中
        return None

    @classmethod
    def set_huawei_config(cls, config: Dict):
        """设置华为云配置缓存"""
        if not cls.is_cache_enabled():
            return

        try:
            key = cls.CACHE_KEYS['huawei_config']
            timeout = cls.CACHE_TIMEOUTS['huawei_config']

            cache.set(key, config, timeout)
            cls._set_local_cache(key, config, min(300, timeout))

            logger.debug("华为云配置缓存已设置")
        except Exception as e:
            logger.error(f"设置华为云配置缓存失败: {str(e)}")

    @classmethod
    @cache_operation('ocr_interfaces', use_local_cache=True)
    def get_ocr_interfaces(cls) -> Optional[Dict]:
        """获取OCR接口缓存"""
        return None

    @classmethod
    def set_ocr_interfaces(cls, interfaces: Dict):
        """设置OCR接口缓存"""
        cls._set_cache('ocr_interfaces', interfaces)

    @classmethod
    @cache_operation('certificate_types', use_local_cache=True)
    def get_certificate_types(cls) -> Optional[Dict]:
        """获取证件类型缓存"""
        return None

    @classmethod
    def set_certificate_types(cls, certificate_types: Dict):
        """设置证件类型缓存"""
        cls._set_cache('certificate_types', certificate_types)

    @classmethod
    @cache_operation('user_records', use_local_cache=False)
    def get_user_records(cls, user_id: int) -> Optional[Dict]:
        """获取用户记录缓存"""
        return None

    @classmethod
    def set_user_records(cls, user_id: int, records: Dict):
        """设置用户记录缓存"""
        key = cls.CACHE_KEYS['user_records'].format(user_id)
        timeout = cls.CACHE_TIMEOUTS['user_records']
        cls._set_cache_with_key(key, records, timeout)

    @classmethod
    @cache_operation('vin_config', use_local_cache=True)
    def get_vin_config(cls) -> Optional[Dict]:
        """获取VIN配置缓存"""
        return None

    @classmethod
    def set_vin_config(cls, config: Dict):
        """设置VIN配置缓存"""
        cls._set_cache('vin_config', config)

    @classmethod
    @cache_operation('vin_query', use_local_cache=True)
    def get_vin_query_result(cls, vin_code: str) -> Optional[Dict]:
        """获取VIN查询结果缓存"""
        return None

    @classmethod
    def set_vin_query_result(cls, vin_code: str, result: Dict):
        """设置VIN查询结果缓存"""
        key = cls.CACHE_KEYS['vin_query'].format(vin_code)
        timeout = cls.CACHE_TIMEOUTS['vin_query']
        cls._set_cache_with_key(key, result, timeout)

    @classmethod
    def _set_cache(cls, cache_type: str, value: Any):
        """通用设置缓存方法"""
        if not cls.is_cache_enabled():
            return

        try:
            key = cls.CACHE_KEYS[cache_type]
            timeout = cls.CACHE_TIMEOUTS[cache_type]
            cls._set_cache_with_key(key, value, timeout)
            logger.debug(f"{cache_type}缓存已设置")
        except Exception as e:
            logger.error(f"设置{cache_type}缓存失败: {str(e)}")

    @classmethod
    def _set_cache_with_key(cls, key: str, value: Any, timeout: int):
        """使用指定键设置缓存"""
        if not cls.is_cache_enabled():
            return

        try:
            # 处理 Django 模型对象
            if hasattr(value, 'to_dict'):
                # 如果对象有 to_dict 方法，使用它
                value = value.to_dict()
            elif hasattr(value, '__dict__'):
                # 尝试将模型对象转换为字典
                try:
                    # 排除内部属性和关系
                    value = {
                        k: v for k, v in value.__dict__.items()
                        if not k.startswith('_') and not callable(v)
                    }
                except Exception as e:
                    logger.warning(f"转换模型对象失败: {str(e)}")
                    value = str(value)

            # 处理 QuerySet 对象
            if hasattr(value, '__iter__') and not isinstance(value, (dict, list, str, int, float, bool, tuple)):
                try:
                    # 如果是 QuerySet，先评估它
                    if hasattr(value, 'count'):
                        value = list(value.values())
                    elif hasattr(value, '__next__'):
                        # 如果是生成器，转换为列表
                        value = list(value)
                except Exception as e:
                    logger.warning(f"无法序列化缓存值 [key={key}]: {str(e)}")
                    return

            # 处理复杂对象，确保可序列化
            try:
                import json
                # 测试是否可 JSON 序列化
                json.dumps(value)
            except (TypeError, ValueError) as e:
                logger.warning(f"缓存值不可 JSON 序列化 [key={key}], 转换为字符串: {str(e)}")
                value = str(value)

            cache.set(key, value, timeout)

            # 同时设置本地缓存，但使用更短的 TTL
            local_ttl = min(300, timeout)
            try:
                cls._set_local_cache(key, value, local_ttl)
            except Exception as e:
                logger.warning(f"设置本地缓存失败 [key={key}]: {str(e)}")

        except Exception as e:
            logger.error(f"设置缓存失败 [key={key}]: {str(e)}")

    @classmethod
    def batch_get(cls, keys: list) -> Dict:
        """批量获取缓存"""
        if not cls.is_cache_enabled() or not keys:
            return {}

        try:
            results = {}
            for key in keys:
                # 先检查本地缓存
                local_result = cls._get_local_cache(key)
                if local_result is not None:
                    results[key] = local_result
                else:
                    redis_result = cache.get(key)
                    if redis_result is not None:
                        results[key] = redis_result
                        # 更新本地缓存
                        cls._set_local_cache(key, redis_result, 300)
            return results
        except Exception as e:
            logger.error(f"批量获取缓存失败: {str(e)}")
            return {}

    @classmethod
    def batch_set(cls, key_value_pairs: Dict, timeout: int = 3600):
        """批量设置缓存"""
        if not cls.is_cache_enabled() or not key_value_pairs:
            return

        try:
            for key, value in key_value_pairs.items():
                cache.set(key, value, timeout)
                cls._set_local_cache(key, value, min(300, timeout))

            logger.debug(f"批量设置 {len(key_value_pairs)} 个缓存项")
        except Exception as e:
            logger.error(f"批量设置缓存失败: {str(e)}")

    @classmethod
    def safe_cache_operation(cls, operation: Callable, *args, **kwargs) -> Any:
        """安全的缓存操作"""
        max_retries = 2
        last_exception = None

        for attempt in range(max_retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"缓存操作失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))

        logger.warning(f"缓存操作最终失败，使用回退: {str(last_exception)}")
        return None

    @classmethod
    def clear_user_records_cache(cls, user_id: int):
        """清除用户记录缓存"""
        key = cls.CACHE_KEYS['user_records'].format(user_id)
        cls.safe_cache_operation(cache.delete, key)

        # 同时清除本地缓存
        if key in cls._local_cache:
            del cls._local_cache[key]
            if key in cls._local_cache_ttl:
                del cls._local_cache_ttl[key]

        logger.debug(f"用户 {user_id} 记录缓存清除操作已完成")

    @classmethod
    def clear_pattern(cls, pattern: str):
        """按模式清除缓存"""
        if not cls.is_cache_enabled():
            return

        try:
            # 注意：keys命令在生产环境可能影响性能
            keys = cache.keys(pattern)
            if keys:
                cache.delete_many(keys)
                logger.info(f"清除模式 '{pattern}' 匹配的 {len(keys)} 个缓存键")

                # 清除匹配的本地缓存
                for key in list(cls._local_cache.keys()):
                    if key.startswith(pattern.replace('*', '')):
                        del cls._local_cache[key]
                        if key in cls._local_cache_ttl:
                            del cls._local_cache_ttl[key]
        except Exception as e:
            logger.error(f"清除模式缓存失败: {str(e)}")

    @classmethod
    def clear_all_cache(cls):
        """清除所有OCR相关缓存"""
        if not cls.is_cache_enabled():
            return

        try:
            # 清除固定键的缓存
            keys_to_delete = []
            for key_name in ['huawei_config', 'ocr_interfaces', 'certificate_types', 'vin_config']:
                keys_to_delete.append(cls.CACHE_KEYS[key_name])

            # 批量删除
            for key in keys_to_delete:
                cache.delete(key)

            # 清除本地缓存
            cls._local_cache.clear()
            cls._local_cache_ttl.clear()

            logger.info("OCR缓存清除操作已完成")
        except Exception as e:
            logger.error(f"清除所有缓存失败: {str(e)}")

    @classmethod
    def get_metrics(cls) -> Dict:
        """获取缓存性能指标"""
        return {
            'hits': cls._metrics.hits,
            'misses': cls._metrics.misses,
            'errors': cls._metrics.errors,
            'total_operations': cls._metrics.total_operations,
            'hit_rate': round(cls._metrics.hit_rate, 4),
            'avg_response_time': round(cls._metrics.avg_response_time, 6),
            'local_cache_size': len(cls._local_cache)
        }

    @classmethod
    def preload_frequent_data(cls):
        """预加载频繁访问的数据"""
        if not cls.is_cache_enabled():
            return

        try:
            # 预加载配置数据
            preload_keys = [
                cls.CACHE_KEYS['huawei_config'],
                cls.CACHE_KEYS['ocr_interfaces'],
                cls.CACHE_KEYS['certificate_types'],
                cls.CACHE_KEYS['vin_config']
            ]

            # 批量获取
            results = cls.batch_get(preload_keys)
            logger.info(f"预加载 {len(results)}/{len(preload_keys)} 个缓存项")
        except Exception as e:
            logger.error(f"预加载缓存失败: {str(e)}")
