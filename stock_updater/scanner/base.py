# -*- coding: utf-8 -*-
"""
需求扫描器基类
"""
from abc import ABC, abstractmethod
from typing import List
from ..models.data_requirement import DataRequirement


class DataRequirementScanner(ABC):
    """数据需求扫描器基类"""
    
    @abstractmethod
    def scan(self) -> List[DataRequirement]:
        """
        扫描并返回数据需求列表
        
        Returns:
            数据需求列表
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """扫描器名称"""
        pass
