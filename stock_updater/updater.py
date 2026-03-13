# -*- coding: utf-8 -*-
"""
股票数据更新器 - 核心协调器
"""
from datetime import date, timedelta
from typing import List, Dict, Optional
from .models.data_requirement import DataRequirement
from .models.missing_data import MissingData
from .models import DataType, SaveMode
from .scanner import ConfigScanner, DatabaseScanner
from .detector import MissingDataDetector
from .fetcher import TushareFetcher
from .storage import SQLiteStorage
from .config import get_config
from .utils import logger


class StockDataUpdater:
    """
    股票数据更新器
    
    整合扫描、检测、获取、存储功能
    """
    
    def __init__(self, config_path: str = None):
        """初始化"""
        # 加载配置
        self.config = get_config(config_path)
        
        # 初始化存储层
        db_path = self.config.database.path
        self.storage = SQLiteStorage(db_path)
        
        # 初始化扫描器
        self.config_scanner = ConfigScanner(
            stock_list=self.config.scan.stock_list,
            data_types=[DataType.OHLCV],
            days_back=self.config.scan.max_backfill_days
        )
        
        self.database_scanner = DatabaseScanner(
            storage=self.storage,
            days_back=self.config.scan.max_backfill_days
        )
        
        # 初始化检测器
        self.detector = MissingDataDetector(self.storage)
        
        # 初始化获取器
        ds_config = self.config.data_sources[0]
        self.fetcher = TushareFetcher(
            api_token=ds_config.api_key,
            rate_limit=ds_config.rate_limit
        )
        
        # 统计信息
        self.stats = {
            'scan_count': 0,
            'missing_count': 0,
            'fetch_count': 0,
            'save_count': 0,
            'errors': []
        }
    
    def scan_requirements(self) -> List[DataRequirement]:
        """
        扫描数据需求
        
        Returns:
            数据需求列表
        """
        logger.info("开始扫描数据需求...")
        
        # 从配置扫描
        config_requirements = self.config_scanner.scan()
        
        # 从数据库扫描
        db_requirements = self.database_scanner.scan()
        
        # 合并去重
        all_requirements = config_requirements + db_requirements
        
        self.stats['scan_count'] = len(all_requirements)
        logger.info(f"共扫描到 {len(all_requirements)} 条数据需求")
        
        return all_requirements
    
    def detect_missing(self, 
                       requirements: List[DataRequirement]) -> List[MissingData]:
        """
        检测缺失数据
        
        Args:
            requirements: 数据需求列表
            
        Returns:
            缺失数据清单
        """
        logger.info("开始检测缺失数据...")
        
        missing = self.detector.detect(requirements)
        
        self.stats['missing_count'] = len(missing)
        logger.info(f"检测到 {len(missing)} 条缺失数据")
        
        return missing
    
    def fetch_and_save(self, 
                        missing: List[MissingData],
                        batch_size: int = 500) -> Dict:
        """
        获取并保存缺失数据
        
        Args:
            missing: 缺失数据清单
            batch_size: 批次大小
            
        Returns:
            处理结果统计
        """
        logger.info(f"开始获取并保存数据 (共 {len(missing)} 项)...")
        
        total_fetched = 0
        total_saved = 0
        errors = []
        
        # 按股票代码分组
        stock_groups: Dict[str, List[MissingData]] = {}
        for m in missing:
            if m.stock_code not in stock_groups:
                stock_groups[m.stock_code] = []
            stock_groups[m.stock_code].append(m)
        
        # 逐只股票处理
        stock_codes = list(stock_groups.keys())
        for i, stock_code in enumerate(stock_codes):
            logger.info(f"[{i+1}/{len(stock_codes)}] 处理 {stock_code}...")
            
            stock_missing = stock_groups[stock_code]
            
            # 合并该股票的所有缺失日期范围
            min_date = min(m.start_date for m in stock_missing)
            max_date = max(m.end_date for m in stock_missing)
            
            try:
                # 获取数据
                records = self.fetcher.fetch(
                    stock_code=stock_code,
                    data_type=DataType.OHLCV,
                    start_date=min_date,
                    end_date=max_date
                )
                
                total_fetched += len(records)
                
                if records:
                    # 保存数据
                    saved = self.storage.save(
                        data_type=DataType.OHLCV,
                        records=records,
                        mode=SaveMode.UPSERT
                    )
                    total_saved += saved
                    logger.info(f"  获取 {len(records)} 条，保存 {saved} 条")
                else:
                    logger.warning(f"  无数据")
                    
            except Exception as e:
                error_msg = f"{stock_code}: {e}"
                errors.append(error_msg)
                logger.error(f"  ❌ 处理失败: {e}")
        
        self.stats['fetch_count'] = total_fetched
        self.stats['save_count'] = total_saved
        self.stats['errors'] = errors
        
        return {
            'total_missing': len(missing),
            'total_fetched': total_fetched,
            'total_saved': total_saved,
            'errors': errors
        }
    
    def sync_for_strategy(self, 
                           stock_codes: List[str] = None,
                           days_back: int = None) -> Dict:
        """
        根据策略需求同步数据（主入口）
        
        Args:
            stock_codes: 股票列表（可选，默认使用配置）
            days_back: 回溯天数（可选，默认使用配置）
            
        Returns:
            同步结果
        """
        logger.info("=" * 50)
        logger.info("开始股票数据同步")
        logger.info("=" * 50)
        
        # 更新股票列表
        if stock_codes:
            self.config_scanner.set_stock_list(stock_codes)
        
        # 更新回溯天数
        if days_back:
            self.config_scanner.days_back = days_back
        
        # 1. 扫描需求
        requirements = self.scan_requirements()
        
        # 2. 检测缺失
        missing = self.detect_missing(requirements)
        
        if not missing:
            logger.info("✅ 数据已是最新，无需更新")
            return {'status': 'ok', 'message': '数据已是最新'}
        
        # 3. 获取并保存
        result = self.fetch_and_save(missing)
        
        logger.info("=" * 50)
        logger.info(f"同步完成: 获取 {result['total_fetched']} 条，保存 {result['total_saved']} 条")
        if result['errors']:
            logger.warning(f"错误: {len(result['errors'])} 个")
        logger.info("=" * 50)
        
        return result
    
    def auto_backfill(self, 
                      stock_codes: List[str] = None,
                      max_days: int = None) -> Dict:
        """
        空闲时自动补充历史数据
        
        触发条件：当没有待处理的策略任务时
        功能：自动向前获取股票的每日数据
        
        Args:
            stock_codes: 股票列表（可选）
            max_days: 最大补数据天数
            
        Returns:
            补数据结果
        """
        logger.info("=" * 50)
        logger.info("开始自动补充历史数据")
        logger.info("=" * 50)
        
        max_days = max_days or self.config.scan.max_backfill_days
        end_date = date.today()
        start_date = end_date - timedelta(days=max_days)
        
        # 使用配置中的股票列表
        if not stock_codes:
            stock_codes = self.config.scan.stock_list
        
        # 检测缺失
        missing = self.detector.detect_for_stocks(
            stock_codes=stock_codes,
            data_type=DataType.OHLCV,
            start_date=start_date,
            end_date=end_date
        )
        
        if not missing:
            logger.info("✅ 历史数据已是最新")
            return {'status': 'ok', 'message': '无需补数据'}
        
        # 获取并保存
        result = self.fetch_and_save(missing)
        
        logger.info("=" * 50)
        logger.info(f"补数据完成: 获取 {result['total_fetched']} 条，保存 {result['total_saved']} 条")
        logger.info("=" * 50)
        
        return result
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        db_stats = self.storage.get_stats()
        return {
            **self.stats,
            'db_stats': db_stats
        }
    
    def test_connection(self) -> bool:
        """测试 API 连接"""
        return self.fetcher.test_connection()
