# -*- coding: utf-8 -*-
"""
配置管理
"""
import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class DataSourceConfig:
    """数据源配置"""
    name: str = "tushare"
    enabled: bool = True
    api_key: str = ""
    rate_limit: float = 5.0  # 每秒调用次数
    
    def __post_init__(self):
        # 从环境变量读取 API Key
        if self.name == "tushare":
            self.api_key = os.environ.get('TUSHARE_TOKEN', self.api_key)


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"
    path: str = "/home/deploy/.openclaw/data/stock.db"
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None


@dataclass
class ScanConfig:
    """扫描配置"""
    config_path: str = "strategies/"
    interval_hours: int = 24
    max_backfill_days: int = 30
    stock_list: list = field(default_factory=lambda: [
        "000001.SZ", "000002.SZ", "600000.SH", "600016.SH", 
        "600030.SH", "600036.SH", "600048.SH", "600050.SH"
    ])


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    file: str = "logs/stock_updater.log"


@dataclass
class StockUpdaterConfig:
    """股票数据更新器配置"""
    data_sources: list = field(default_factory=lambda: [DataSourceConfig()])
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    scan: ScanConfig = field(default_factory=ScanConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_yaml(cls, path: str) -> 'StockUpdaterConfig':
        """从 YAML 文件加载配置"""
        config_file = Path(path)
        if not config_file.exists():
            return cls()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        if 'stock_updater' in data:
            data = data['stock_updater']
        
        # 构建配置对象
        data_sources = []
        for ds in data.get('data_sources', []):
            data_sources.append(DataSourceConfig(**ds))
        if not data_sources:
            data_sources.append(DataSourceConfig())
        
        return cls(
            data_sources=data_sources,
            database=DatabaseConfig(**data.get('database', {})),
            scan=ScanConfig(**data.get('scan', {})),
            logging=LoggingConfig(**data.get('logging', {}))
        )


# 全局配置实例
_config: Optional[StockUpdaterConfig] = None


def get_config(config_path: Optional[str] = None) -> StockUpdaterConfig:
    """获取全局配置"""
    global _config
    if _config is None:
        if config_path:
            _config = StockUpdaterConfig.from_yaml(config_path)
        else:
            # 默认配置
            _config = StockUpdaterConfig()
    return _config


def set_config(config: StockUpdaterConfig) -> None:
    """设置全局配置"""
    global _config
    _config = config
