# -*- coding: utf-8 -*-
"""
数据获取器基类
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, Dict
import time
from ..models import DataSource, SourceConfig


class DataFetcher(ABC):
    """数据获取器抽象基类"""
    
    def __init__(self, source: DataSource, config: SourceConfig = None):
        self.source = source
        self.config = config or SourceConfig(name=source)
        self._last_call_time = 0
    
    @property
    def source_name(self) -> str:
        return self.source.value
    
    @property
    def weight(self) -> float:
        return self.config.weight
    
    @property
    def is_enabled(self) -> bool:
        return self.config.enabled and not self.config.disabled
    
    @property
    def is_free(self) -> bool:
        """是否为免费数据源"""
        return self.source in [DataSource.AKSHARE, DataSource.BAOSTOCK]
    
    def _rate_limit_wait(self, min_interval: float = 0.2):
        """速率限制"""
        elapsed = time.time() - self._last_call_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_call_time = time.time()
    
    def record_failure(self):
        """记录失败"""
        self.config.consecutive_failures += 1
        if self.is_free and self.config.consecutive_failures >= 3:
            self.config.disabled = True
            print(f"⚠️ {self.source_name} 连续3次失败，已禁用")
    
    def record_success(self):
        """记录成功"""
        self.config.consecutive_failures = 0
    
    @abstractmethod
    def fetch(self,
              stock_code: str,
              trade_date: date) -> Optional[Dict]:
        """
        获取数据
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期
            
        Returns:
            数据字典或 None
        """
        pass
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            result = self.fetch("000001.SZ", date.today())
            return result is not None
        except Exception:
            return False
