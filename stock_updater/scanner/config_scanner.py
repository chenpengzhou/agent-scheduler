# -*- coding: utf-8 -*-
"""
配置扫描器 - 从配置中读取数据需求
"""
import os
from datetime import date, timedelta
from typing import List
from .base import DataRequirementScanner
from ..models.data_requirement import DataRequirement
from ..models import DataType


class ConfigScanner(DataRequirementScanner):
    """从配置文件扫描数据需求"""
    
    def __init__(self, stock_list: List[str] = None, 
                 data_types: List[DataType] = None,
                 days_back: int = 30):
        """
        初始化配置扫描器
        
        Args:
            stock_list: 股票列表
            data_types: 数据类型列表
            days_back: 回溯天数
        """
        self.stock_list = stock_list or []
        self.data_types = data_types or [DataType.OHLCV]
        self.days_back = days_back
    
    @property
    def name(self) -> str:
        return "config"
    
    def scan(self) -> List[DataRequirement]:
        """扫描数据需求"""
        requirements = []
        
        end_date = date.today()
        start_date = end_date - timedelta(days=self.days_back)
        
        for stock_code in self.stock_list:
            for data_type in self.data_types:
                req = DataRequirement(
                    stock_code=stock_code,
                    data_type=data_type,
                    start_date=start_date,
                    end_date=end_date
                )
                requirements.append(req)
        
        print(f"📋 ConfigScanner 扫描到 {len(requirements)} 条数据需求")
        return requirements
    
    def add_stock(self, stock_code: str):
        """添加股票"""
        if stock_code not in self.stock_list:
            self.stock_list.append(stock_code)
    
    def set_stock_list(self, stock_list: List[str]):
        """设置股票列表"""
        self.stock_list = stock_list


class DatabaseScanner(DataRequirementScanner):
    """从数据库扫描策略所需数据"""
    
    def __init__(self, storage, days_back: int = 30):
        """
        初始化数据库扫描器
        
        Args:
            storage: 数据存储实例
            days_back: 回溯天数
        """
        self.storage = storage
        self.days_back = days_back
    
    @property
    def name(self) -> str:
        return "database"
    
    def scan(self) -> List[DataRequirement]:
        """从数据库已有数据中识别需求"""
        requirements = []
        
        # 获取所有已有的股票代码
        stock_codes = self.storage.get_all_stock_codes()
        
        if not stock_codes:
            print("⚠️ 数据库中暂无股票数据")
            return requirements
        
        end_date = date.today()
        start_date = end_date - timedelta(days=self.days_back)
        
        for stock_code in stock_codes:
            # 检查每只股票的数据完整性
            data_range = self.storage.get_data_range(stock_code, DataType.OHLCV)
            
            if data_range[0] is None:
                # 完全没有数据，需要完整获取
                req = DataRequirement(
                    stock_code=stock_code,
                    data_type=DataType.OHLCV,
                    start_date=start_date,
                    end_date=end_date
                )
                requirements.append(req)
            else:
                # 有部分数据，检查是否需要补充
                if data_range[0] > start_date:
                    # 缺少早期数据
                    req = DataRequirement(
                        stock_code=stock_code,
                        data_type=DataType.OHLCV,
                        start_date=start_date,
                        end_date=data_range[0] - timedelta(days=1)
                    )
                    requirements.append(req)
                
                if data_range[1] < end_date - timedelta(days=1):
                    # 缺少近期数据
                    req = DataRequirement(
                        stock_code=stock_code,
                        data_type=DataType.OHLCV,
                        start_date=data_range[1] + timedelta(days=1),
                        end_date=end_date
                    )
                    requirements.append(req)
        
        print(f"📋 DatabaseScanner 扫描到 {len(requirements)} 条数据需求")
        return requirements
