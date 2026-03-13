# -*- coding: utf-8 -*-
"""
股票数据更新模块

功能：
1. 数据需求扫描 - 扫描策略配置文件/数据库
2. 数据缺失检测 - 对比需求与本地数据库
3. API获取 - 调用外部API获取缺失数据
4. 本地存储 - 写入SQLite数据库
5. 空闲时自动补充历史数据

使用示例：
    python -m stock_updater sync                    # 同步数据
    python -m stock_updater backfill                 # 补历史数据
    python -m stock_updater scan                     # 仅扫描需求
    python -m stock_updater stats                    # 查看统计
    python -m stock_updater test                     # 测试API连接
"""

from .updater import StockDataUpdater
from .config import get_config, StockUpdaterConfig
from .models.data_requirement import DataRequirement
from .models.missing_data import MissingData
from .models import DataType, SaveMode

__version__ = "1.0.0"

__all__ = [
    'StockDataUpdater',
    'get_config',
    'StockUpdaterConfig',
    'DataRequirement',
    'MissingData',
    'DataType',
    'SaveMode'
]
