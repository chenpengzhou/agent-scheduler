# -*- coding: utf-8 -*-
"""
股票数据验证器 - 核心协调器
"""
from datetime import date
from typing import List, Dict, Optional
from .fetcher import (
    DataFetcher, TushareFetcher, JuqingFetcher, 
    BaostockFetcher, AkShareFetcher, DataSource
)
from .validator import RuleEngine
from .handler import ConsistentHandler, InconsistentHandler, SingleSourceHandler
from .models import VerifyRequest, VerifyResult, VerifyStatus


class StockDataVerifier:
    """股票数据验证器"""
    
    def __init__(self, db_path: str = "/home/robin/.openclaw/data/stock.db"):
        self.db_path = db_path
        
        # 初始化数据获取器
        self.fetchers: Dict[str, DataFetcher] = {}
        self._init_fetchers()
        
        # 初始化验证引擎
        self.rule_engine = RuleEngine()
        
        # 初始化处理器
        self.consistent_handler = ConsistentHandler(db_path)
        self.inconsistent_handler = InconsistentHandler(db_path)
        self.single_handler = SingleSourceHandler(db_path)
        
        # 统计
        self.stats = {
            'total': 0,
            'consistent': 0,
            'inconsistent': 0,
            'single_source': 0,
            'error': 0
        }
    
    def _init_fetchers(self):
        """初始化数据获取器"""
        # Tushare (主源)
        tushare = TushareFetcher()
        if tushare.is_enabled:
            self.fetchers['tushare'] = tushare
            print(f"✅ Tushare 已启用 (权重: 40%)")
        
        # 聚宽
        juqing = JuqingFetcher()
        if juqing.is_enabled:
            self.fetchers['聚宽'] = juqing
            print(f"✅ 聚宽已启用 (权重: 30%)")
        
        # Baostock
        baostock = BaostockFetcher()
        if baostock.is_enabled:
            self.fetchers['baostock'] = baostock
            print(f"✅ Baostock已启用 (权重: 20%)")
        
        # AkShare
        akshare = AkShareFetcher()
        if akshare.is_enabled:
            self.fetchers['akshare'] = akshare
            print(f"✅ AkShare已启用 (权重: 10%)")
        
        print(f"\n已初始化 {len(self.fetchers)} 个数据源")
    
    def verify(self, request: VerifyRequest) -> VerifyResult:
        """
        验证单条数据
        
        Args:
            request: 验证请求
            
        Returns:
            验证结果
        """
        self.stats['total'] += 1
        
        # 1. 并行获取多源数据
        sources_data = self._fetch_all_sources(
            request.stock_code,
            request.trade_date
        )
        
        # 2. 执行验证
        result = self.rule_engine.verify(
            sources_data=sources_data,
            stock_code=request.stock_code,
            trade_date=request.trade_date.strftime('%Y%m%d'),
            data_type=request.data_types[0].value if request.data_types else 'ohlcv'
        )
        
        # 3. 根据状态处理
        success = self._handle_result(result)
        
        # 4. 更新统计
        if result.status == VerifyStatus.CONSISTENT:
            self.stats['consistent'] += 1
        elif result.status == VerifyStatus.INCONSISTENT:
            self.stats['inconsistent'] += 1
        elif result.status == VerifyStatus.SINGLE_SOURCE:
            self.stats['single_source'] += 1
        else:
            self.stats['error'] += 1
        
        return result
    
    def verify_batch(self, requests: List[VerifyRequest]) -> List[VerifyResult]:
        """
        批量验证
        
        Args:
            requests: 验证请求列表
            
        Returns:
            验证结果列表
        """
        results = []
        for req in requests:
            result = self.verify(req)
            results.append(result)
        return results
    
    def _fetch_all_sources(self, stock_code: str, 
                           trade_date: date) -> Dict[str, Optional[Dict]]:
        """获取所有数据源的数据"""
        sources_data = {}
        
        for source_name, fetcher in self.fetchers.items():
            if fetcher.is_enabled:
                try:
                    data = fetcher.fetch(stock_code, trade_date)
                    sources_data[source_name] = data
                    
                    if data:
                        print(f"  ✓ {source_name}: 获取成功")
                    else:
                        print(f"  ✗ {source_name}: 无数据")
                        
                except Exception as e:
                    print(f"  ✗ {source_name}: {e}")
                    sources_data[source_name] = None
            else:
                sources_data[source_name] = None
        
        return sources_data
    
    def _handle_result(self, result: VerifyResult) -> bool:
        """处理验证结果"""
        if result.status == VerifyStatus.CONSISTENT:
            return self.consistent_handler.handle(result)
        elif result.status == VerifyStatus.INCONSISTENT:
            return self.inconsistent_handler.handle(result)
        elif result.status == VerifyStatus.SINGLE_SOURCE:
            return self.single_handler.handle(result)
        else:
            return False
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'enabled_sources': list(self.fetchers.keys()),
            'db_path': self.db_path
        }
    
    def get_disabled_sources(self) -> List[str]:
        """获取被禁用的数据源"""
        disabled = []
        for name, fetcher in self.fetchers.items():
            if fetcher.config.disabled:
                disabled.append(name)
        return disabled
    
    def reset_disabled_sources(self):
        """重置被禁用的数据源"""
        for fetcher in self.fetchers.values():
            fetcher.config.disabled = False
            fetcher.config.consecutive_failures = 0
        print("✅ 已重置所有被禁用的数据源")
