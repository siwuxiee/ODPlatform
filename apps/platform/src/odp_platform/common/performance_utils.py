#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : performance_utils.py
# @Time      : 2026/5/19 14:03:58
# @Author    : 雨霓同学
# @Project   : ODPlatform
# @Function  : 性能测试工具

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def time_it(iterations: int = 1, 
            name: str = None, 
            logger_instance: logging.Logger = None):
    """
    通用执行时间测试装饰器
    :param iterations: 执行次数
    :param name: 执行操作的名称
    :param logger_instance: 日志的实例对象
    """
    log = logger_instance if logger_instance is not None else logger

    def _format_time_auto_unit(seconds: float | int) -> str:
        """
        自动选择合适的时间单位
        :param seconds: 秒数
        :return: 格式化后的时间字符串
        """
        if seconds < 0.001:
            return f"{seconds * 1_000_000:.3f} 微秒"
        elif seconds < 1.0:
            return f"{seconds * 1_000:.3f} 毫秒"
        elif seconds < 60.0:
            return f"{seconds:.3f} 秒"
        elif seconds < 3600.0:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins:.0f} 分钟 {secs:.3f} 秒"
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            secs = (seconds % 3600) % 60
            return f"{hours:.0f} 小时 {mins:.0f} 分钟 {secs:.3f} 秒"

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            display_name = name if name is not None else func.__name__
            total = 0.0
            result = None
            
            for _ in range(iterations):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                end = time.perf_counter()
                total += end - start
                
            avg = total / iterations
            avg_str = _format_time_auto_unit(avg)
            
            if iterations == 1:
                log.info(f"性能报告: [{display_name}] 执行耗时 {avg_str}")
            else:
                total_str = _format_time_auto_unit(total)
                log.info(f"性能报告: [{display_name}] 执行了 {iterations}次, 总耗时 {total_str} | 平均耗时 {avg_str}")
                
            return result
        return wrapper
    return decorator

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    @time_it(name="测试函数-睡眠0.5s")
    def test_func():
        time.sleep(0.5)
        print("测试函数执行完毕")
        
    @time_it(name="测试快函数", iterations=10)
    def test_fast_func():
        time.sleep(0.01)
        
    test_func()
    test_fast_func()