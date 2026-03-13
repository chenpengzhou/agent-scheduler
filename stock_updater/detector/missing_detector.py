# -*- coding: utf-8 -*-
"""
缺失数据检测器
"""
from datetime import date, timedelta
from typing import List
from ..models.data_requirement import DataRequirement
from ..models.missing_data import MissingData
from ..models import DataType
from ..storage.base import DataStorage


class MissingDataDetector:
    """缺失数据检测器"""
    
    def __init__(self, storage: DataStorage):
        self.storage = storage
    
    def detect(self, 
               requirements: List[DataRequirement]) -> List[MissingData]:
        """
        检测缺失数据
        
        Args:
            requirements: 数据需求列表
            
        Returns:
            缺失数据清单
        """
        missing_list = []
        
        for req in requirements:
            missing = self._detect_single(req)
            if missing:
                missing_list.extend(missing)
        
        print(f"🔍 检测到 {len(missing_list)} 条缺失数据")
        return missing_list
    
    def _detect_single(self, requirement: DataRequirement) -> List[MissingData]:
        """检测单条需求的缺失数据"""
        stock_code = requirement.stock_code
        data_type = requirement.data_type
        req_start = requirement.start_date
        req_end = requirement.end_date or date.today()
        
        # 获取本地已有数据的日期范围
        local_range = self.storage.get_data_range(stock_code, data_type)
        local_start, local_end = local_range
        
        missing_list = []
        
        if local_start is None and local_end is None:
            # 本地完全没有数据，整个范围都缺失
            missing = MissingData(
                stock_code=stock_code,
                data_type=data_type,
                start_date=req_start,
                end_date=req_end,
                reason="本地无数据"
            )
            missing_list.append(missing)
        else:
            # 检查起始日期之前的缺失
            if local_start and req_start < local_start:
                missing = MissingData(
                    stock_code=stock_code,
                    data_type=data_type,
                    start_date=req_start,
                    end_date=local_start - timedelta(days=1),
                    reason="缺少早期数据"
                )
                missing_list.append(missing)
            
            # 检查日期之间的缺失（周末、节假日等）
            if local_start and local_end:
                # 简化处理：只检查头尾
                pass
            
            # 检查结束日期之后的缺失
            if local_end and req_end > local_end:
                missing = MissingData(
                    stock_code=stock_code,
                    data_type=data_type,
                    start_date=local_end + timedelta(days=1),
                    end_date=req_end,
                    reason="缺少近期数据"
                )
                missing_list.append(missing)
        
        return missing_list
    
    def detect_for_stocks(self, 
                          stock_codes: List[str],
                          data_type: DataType,
                          start_date: date,
                          end_date: date) -> List[MissingData]:
        """
        批量检测多只股票的缺失数据
        
        Args:
            stock_codes: 股票代码列表
            data_type: 数据类型
            start_date: 起始日期
            end_date: 结束日期
            
        Returns:
            缺失数据清单
        """
        requirements = [
            DataRequirement(
                stock_code=code,
                data_type=data_type,
                start_date=start_date,
                end_date=end_date
            )
            for code in stock_codes
        ]
        
        return self.detect(requirements)
    
    def group_by_date(self, 
                       missing_list: List[MissingData]) -> dict:
        """
        按日期范围分组缺失数据
        
        Returns:
            {date_range: [MissingData]}
        """
        grouped = {}
        for m in missing_list:
            key = f"{m.start_date}~{m.end_date}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(m)
        return grouped
