# -*- coding: utf-8 -*-
"""
测试入口脚本 - 设置正确的 Python 路径
"""
import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.expanduser("~/.openclaw/workspace-dev")
sys.path.insert(0, PROJECT_ROOT)

# 正确设置 stock_updater 包
import stock_updater
stock_updater.__path__ = [os.path.join(PROJECT_ROOT, 'stock_updater')]

# 现在可以正常导入
from stock_updater.models import DataType, SaveMode
from stock_updater.models.data_requirement import DataRequirement
from stock_updater.models.missing_data import MissingData
from stock_updater.scanner.config_scanner import ConfigScanner, DatabaseScanner
from stock_updater.detector.missing_detector import MissingDataDetector
from stock_updater.storage.sqlite_storage import SQLiteStorage
from stock_updater.fetcher.tushare_fetcher import TushareFetcher

# 导出供测试使用
__all__ = [
    'DataType', 'SaveMode',
    'DataRequirement', 'MissingData',
    'ConfigScanner', 'DatabaseScanner',
    'MissingDataDetector',
    'SQLiteStorage',
    'TushareFetcher'
]
