# -*- coding: utf-8 -*-
"""
重试装饰器
"""
import time
import functools
from typing import Callable, Type, Tuple


def retry(max_retries: int = 3, 
          backoff_factor: float = 2.0,
          exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        print(f"⚠️ 第 {attempt + 1} 次尝试失败: {e}, {wait_time:.1f}s 后重试...")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ 全部 {max_retries} 次尝试失败: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator
