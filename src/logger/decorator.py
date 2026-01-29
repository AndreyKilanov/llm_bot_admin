import functools
import logging
import time
from typing import Any, Callable

def log_function(func: Callable) -> Callable:
    """Декоратор для логирования вызова функции, её аргументов и результата."""
    logger = logging.getLogger(f"func.{func.__module__}")

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        func_name = f"{func.__module__}.{func.__qualname__}"
        
        logger.debug("Вызов функции %s | args: %s | kwargs: %s", func_name, args, kwargs)
        
        try:
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            logger.info("Успешное выполнение %s | Время: %.4fs", func_name, duration)
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error("Ошибка в %s | Исключение: %s | Время: %.4fs", func_name, e, duration, exc_info=True)
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        func_name = f"{func.__module__}.{func.__qualname__}"
        
        logger.debug("Вызов функции %s | args: %s | kwargs: %s", func_name, args, kwargs)
        
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            logger.info("Успешное выполнение %s | Время: %.4fs", func_name, duration)
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error("Ошибка в %s | Исключение: %s | Время: %.4fs", func_name, e, duration, exc_info=True)
            raise

    if (
        hasattr(func, "__code__") 
        and (func.__code__.co_flags & 0x80) # CO_COROUTINE
        or (func.__code__.co_flags & 0x100) # CO_ITERABLE_COROUTINE
    ):
        return async_wrapper
    
    # Simple check for async functions created via async def
    if hasattr(func, "_is_coroutine") or (hasattr(func, "__code__") and func.__code__.co_flags & 0x80):
         return async_wrapper
         
    import inspect
    if inspect.iscoroutinefunction(func):
        return async_wrapper
        
    return sync_wrapper
