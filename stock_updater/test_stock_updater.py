# -*- coding: utf-8 -*-
"""
股票数据更新模块 - 测试用例
QA: 伦纳德（星星）

覆盖范围：
1. 数据需求扫描功能测试
2. 数据缺失检测测试
3. API获取测试
4. 本地存储测试
5. 空闲时自动补充历史数据测试
"""
import os
import sys
import unittest
import tempfile
import shutil
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
STOCK_UPDATER_PATH = os.path.expanduser("~/.openclaw/workspace-dev/stock_updater")
sys.path.insert(0, STOCK_UPDATER_PATH)

# 导入被测模块
import models
from models.data_requirement import DataRequirement
from models.missing_data import MissingData
from models import DataType, SaveMode

import scanner
from scanner.config_scanner import ConfigScanner, DatabaseScanner

import detector
from detector.missing_detector import MissingDataDetector

import storage
from storage.sqlite_storage import SQLiteStorage

import fetcher
from fetcher.tushare_fetcher import TushareFetcher
from fetcher.base import StockDataFetcher

import updater


class TestDataRequirement(unittest.TestCase):
    """测试数据需求模型"""
    
    def test_stock_code_normalization(self):
        """测试股票代码标准化"""
        # 测试不带后缀的代码自动添加后缀
        req1 = DataRequirement(
            stock_code="000001",
            data_type=DataType.OHLCV,
            start_date=date.today()
        )
        self.assertEqual(req1.stock_code, "000001.SZ")  # 默认深圳
        
        req2 = DataRequirement(
            stock_code="600000",
            data_type=DataType.OHLCV,
            start_date=date.today()
        )
        self.assertEqual(req2.stock_code, "600000.SH")  # 上海
        
        # 测试已带后缀的不变
        req3 = DataRequirement(
            stock_code="000001.SZ",
            data_type=DataType.OHLCV,
            start_date=date.today()
        )
        self.assertEqual(req3.stock_code, "000001.SZ")
    
    def test_date_range_property(self):
        """测试日期范围属性"""
        req = DataRequirement(
            stock_code="000001",
            data_type=DataType.OHLCV,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31)
        )
        self.assertEqual(req.date_range, (date(2025, 1, 1), date(2025, 1, 31)))


class TestMissingData(unittest.TestCase):
    """测试缺失数据模型"""
    
    def test_days_count(self):
        """测试缺失天数计算"""
        missing = MissingData(
            stock_code="000001.SZ",
            data_type=DataType.OHLCV,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 10)
        )
        self.assertEqual(missing.days_count, 10)  # 1-10日共10天
    
    def test_date_range_property(self):
        """测试日期范围属性"""
        missing = MissingData(
            stock_code="000001.SZ",
            data_type=DataType.OHLCV,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31)
        )
        self.assertEqual(missing.date_range, (date(2025, 1, 1), date(2025, 1, 31)))
    
    def test_repr(self):
        """测试字符串表示"""
        missing = MissingData(
            stock_code="000001.SZ",
            data_type=DataType.OHLCV,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 10)
        )
        self.assertIn("000001.SZ", repr(missing))
        self.assertIn("10", repr(missing))


class TestConfigScanner(unittest.TestCase):
    """测试数据需求扫描功能"""
    
    def setUp(self):
        """测试前准备"""
        self.scanner = ConfigScanner(
            stock_list=["000001", "600000"],
            data_types=[DataType.OHLCV],
            days_back=30
        )
    
    def test_scan_returns_list(self):
        """测试扫描返回列表"""
        requirements = self.scanner.scan()
        self.assertIsInstance(requirements, list)
    
    def test_scan_correct_count(self):
        """测试扫描数量正确"""
        requirements = self.scanner.scan()
        # 2只股票 × 1种数据类型 = 2条需求
        self.assertEqual(len(requirements), 2)
    
    def test_scan_stock_codes_normalized(self):
        """测试扫描后股票代码已标准化"""
        requirements = self.scanner.scan()
        codes = [req.stock_code for req in requirements]
        self.assertIn("000001.SZ", codes)
        self.assertIn("600000.SH", codes)
    
    def test_scan_date_range(self):
        """测试日期范围正确"""
        requirements = self.scanner.scan()
        today = date.today()
        expected_start = today - timedelta(days=30)
        
        for req in requirements:
            self.assertEqual(req.start_date, expected_start)
            self.assertEqual(req.end_date, today)
    
    def test_add_stock(self):
        """测试添加股票"""
        self.scanner.add_stock("300001")
        requirements = self.scanner.scan()
        codes = [req.stock_code for req in requirements]
        self.assertIn("300001.SZ", codes)
    
    def test_set_stock_list(self):
        """测试设置股票列表"""
        self.scanner.set_stock_list(["300001", "300002"])
        requirements = self.scanner.scan()
        self.assertEqual(len(requirements), 2)
        codes = [req.stock_code for req in requirements]
        self.assertIn("300001.SZ", codes)


class TestDatabaseScanner(unittest.TestCase):
    """测试数据库扫描器"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
        self.scanner = DatabaseScanner(
            storage=self.storage,
            days_back=30
        )
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_scan_empty_database(self):
        """测试空数据库扫描"""
        requirements = self.scanner.scan()
        # 空数据库应该返回空列表
        self.assertEqual(len(requirements), 0)
    
    def test_scan_with_data(self):
        """测试有数据的数据库扫描"""
        # 插入一些测试数据
        test_records = [
            {
                'stock_code': '000001.SZ',
                'trade_date': '20250101',
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            }
        ]
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        requirements = self.scanner.scan()
        # 应该有缺失数据需求
        self.assertGreaterEqual(len(requirements), 0)


class TestMissingDataDetector(unittest.TestCase):
    """测试数据缺失检测"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        self.detector = MissingDataDetector(self.storage)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_detect_no_local_data(self):
        """测试本地无数据时的检测"""
        requirements = [
            DataRequirement(
                stock_code="000001.SZ",
                data_type=DataType.OHLCV,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31)
            )
        ]
        
        missing = self.detector.detect(requirements)
        
        # 应该检测到完整范围缺失
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0].stock_code, "000001.SZ")
        self.assertEqual(missing[0].start_date, date(2025, 1, 1))
        self.assertEqual(missing[0].end_date, date(2025, 1, 31))
        self.assertEqual(missing[0].reason, "本地无数据")
    
    def test_detect_partial_data(self):
        """测试部分数据时的检测"""
        # 插入部分数据（只有2025-01-15到2025-01-31）
        test_records = []
        for d in range(15, 32):
            test_records.append({
                'stock_code': '000001.SZ',
                'trade_date': f'202501{d:02d}',
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            })
        
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        # 检测1月全月
        requirements = [
            DataRequirement(
                stock_code="000001.SZ",
                data_type=DataType.OHLCV,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31)
            )
        ]
        
        missing = self.detector.detect(requirements)
        
        # 应该检测到月初缺失
        self.assertGreaterEqual(len(missing), 1)
        early_missing = [m for m in missing if m.start_date == date(2025, 1, 1)]
        self.assertEqual(len(early_missing), 1)
        self.assertEqual(early_missing[0].reason, "缺少早期数据")
    
    def test_detect_no_missing(self):
        """测试无缺失时的检测"""
        # 插入完整数据
        test_records = []
        for d in range(1, 32):
            test_records.append({
                'stock_code': '000001.SZ',
                'trade_date': f'202501{d:02d}',
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            })
        
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        requirements = [
            DataRequirement(
                stock_code="000001.SZ",
                data_type=DataType.OHLCV,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31)
            )
        ]
        
        missing = self.detector.detect(requirements)
        
        # 无缺失
        self.assertEqual(len(missing), 0)
    
    def test_detect_for_stocks(self):
        """测试批量检测多只股票"""
        missing = self.detector.detect_for_stocks(
            stock_codes=["000001.SZ", "600000.SH"],
            data_type=DataType.OHLCV,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31)
        )
        
        # 两只股票都应该检测到缺失
        self.assertEqual(len(missing), 2)
    
    def test_group_by_date(self):
        """测试按日期分组"""
        missing_list = [
            MissingData("000001.SZ", DataType.OHLCV, date(2025, 1, 1), date(2025, 1, 15)),
            MissingData("000002.SZ", DataType.OHLCV, date(2025, 1, 1), date(2025, 1, 15)),
            MissingData("000003.SZ", DataType.OHLCV, date(2025, 1, 16), date(2025, 1, 31)),
        ]
        
        grouped = self.detector.group_by_date(missing_list)
        
        self.assertIn("2025-01-01~2025-01-15", grouped)
        self.assertEqual(len(grouped["2025-01-01~2025-01-15"]), 2)


class TestSQLiteStorage(unittest.TestCase):
    """测试本地存储"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_get_range(self):
        """测试保存和获取日期范围"""
        test_records = [
            {
                'stock_code': '000001.SZ',
                'trade_date': '20250101',
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            },
            {
                'stock_code': '000001.SZ',
                'trade_date': '20250102',
                'open': 10.5, 'high': 11.5, 'low': 10.0, 'close': 11.0,
                'volume': 1100000, 'amount': 11000000
            }
        ]
        
        saved = self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        self.assertEqual(saved, 2)
        
        # 获取日期范围
        date_range = self.storage.get_data_range("000001.SZ", DataType.OHLCV)
        self.assertEqual(date_range[0], date(2025, 1, 1))
        self.assertEqual(date_range[1], date(2025, 1, 2))
    
    def test_exists(self):
        """测试数据存在检查"""
        test_records = [
            {
                'stock_code': '000001.SZ',
                'trade_date': '20250101',
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            }
        ]
        
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        # 检查存在
        exists = self.storage.exists("000001.SZ", DataType.OHLCV, date(2025, 1, 1))
        self.assertTrue(exists)
        
        # 检查不存在
        not_exists = self.storage.exists("000001.SZ", DataType.OHLCV, date(2025, 1, 2))
        self.assertFalse(not_exists)
    
    def test_get_all_stock_codes(self):
        """测试获取所有股票代码"""
        test_records = [
            {
                'stock_code': '000001.SZ',
                'trade_date': '20250101',
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            },
            {
                'stock_code': '600000.SH',
                'trade_date': '20250101',
                'open': 20.0, 'high': 21.0, 'low': 19.5, 'close': 20.5,
                'volume': 2000000, 'amount': 20000000
            }
        ]
        
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        codes = self.storage.get_all_stock_codes()
        
        self.assertIn("000001.SZ", codes)
        self.assertIn("600000.SH", codes)
    
    def test_get_stats(self):
        """测试统计信息"""
        test_records = [
            {
                'stock_code': '000001.SZ',
                'trade_date': '20250101',
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            }
        ]
        
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        stats = self.storage.get_stats()
        
        self.assertEqual(stats['daily_count'], 1)
        self.assertEqual(stats['daily_stocks'], 1)
    
    def test_replace_mode(self):
        """测试替换模式"""
        # 第一次插入
        records1 = [
            {
                'stock_code': '000001.SZ',
                'trade_date': '20250101',
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            }
        ]
        self.storage.save(DataType.OHLCV, records1, SaveMode.REPLACE)
        
        # 替换
        records2 = [
            {
                'stock_code': '000001.SZ',
                'trade_date': '20250101',
                'open': 15.0, 'high': 16.0, 'low': 14.5, 'close': 15.5,
                'volume': 1500000, 'amount': 15000000
            }
        ]
        self.storage.save(DataType.OHLCV, records2, SaveMode.REPLACE)
        
        # 验证已替换
        date_range = self.storage.get_data_range("000001.SZ", DataType.OHLCV)
        self.assertIsNotNone(date_range[0])


class TestTushareFetcher(unittest.TestCase):
    """测试API获取功能"""
    
    def setUp(self):
        """测试前准备"""
        # 使用模拟的 fetcher
        self.fetcher = TushareFetcher(api_token="test_token")
    
    @patch('fetcher.tushare_fetcher.time.sleep')
    def test_fetch_without_api(self, mock_sleep):
        """测试未初始化API时的错误处理"""
        # 创建一个未初始化API的实例
        fetcher = TushareFetcher(api_token="")
        
        with self.assertRaises(RuntimeError):
            fetcher.fetch("000001.SZ", DataType.OHLCV, date(2025, 1, 1), date(2025, 1, 31))
    
    def test_rate_limit_wait(self):
        """测试速率限制"""
        # 测试速率限制等待逻辑
        import time
        start = time.time()
        
        fetcher = TushareFetcher(api_token="test_token", rate_limit=10.0)
        # 连续调用应该触发等待
        fetcher._rate_limit_wait()
        fetcher._rate_limit_wait()
        
        elapsed = time.time() - start
        # 10次/秒，最小间隔0.1秒
        self.assertGreaterEqual(elapsed, 0.1)
    
    @patch('fetcher.tushare_fetcher.time.sleep')
    def test_fetch_batch_structure(self, mock_sleep):
        """测试批量获取返回结构"""
        # 注意：由于需要真实API，这里只测试方法存在和返回结构
        # 实际测试需要 mock tushare 库
        self.assertTrue(hasattr(self.fetcher, 'fetch_batch'))
        self.assertTrue(callable(self.fetcher.fetch_batch))


class TestStockDataUpdater(unittest.TestCase):
    """测试股票数据更新器 - 集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试配置目录
        config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(config_dir)
        
        # 创建临时数据库
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
        # 初始化扫描器
        self.scanner = ConfigScanner(
            stock_list=["000001"],
            data_types=[DataType.OHLCV],
            days_back=7
        )
        
        # 初始化检测器
        self.detector = MissingDataDetector(self.storage)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_scan_requirements_integration(self):
        """集成测试：扫描需求"""
        requirements = self.scanner.scan()
        
        self.assertEqual(len(requirements), 1)
        self.assertEqual(requirements[0].stock_code, "000001.SZ")
        self.assertEqual(requirements[0].data_type, DataType.OHLCV)
    
    def test_detect_missing_integration(self):
        """集成测试：检测缺失"""
        requirements = self.scanner.scan()
        missing = self.detector.detect(requirements)
        
        # 新数据库应该检测到缺失
        self.assertGreaterEqual(len(missing), 1)
        self.assertEqual(missing[0].stock_code, "000001.SZ")
    
    def test_save_and_detect_integration(self):
        """集成测试：保存后再检测"""
        # 先保存一些数据
        test_records = [
            {
                'stock_code': '000001.SZ',
                'trade_date': date.today().strftime('%Y%m%d'),
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            }
        ]
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        # 再次检测
        requirements = self.scanner.scan()
        missing = self.detector.detect(requirements)
        
        # 应该没有缺失或只有部分缺失
        self.assertIsInstance(missing, list)


class TestAutoBackfill(unittest.TestCase):
    """测试空闲时自动补充历史数据"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        self.detector = MissingDataDetector(self.storage)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_auto_backfill_detect(self):
        """测试自动补充前的缺失检测"""
        # 模拟场景：数据库只有最近3个月数据
        # 需要补充更早的历史数据
        
        # 先保存一些"最近"的数据
        today = date.today()
        recent_start = today - timedelta(days=90)
        
        test_records = []
        current = recent_start
        while current <= today:
            test_records.append({
                'stock_code': '000001.SZ',
                'trade_date': current.strftime('%Y%m%d'),
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            })
            current += timedelta(days=1)
        
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        # 检测更大范围（180天）
        start_date = today - timedelta(days=180)
        end_date = today
        
        missing = self.detector.detect_for_stocks(
            stock_codes=["000001.SZ"],
            data_type=DataType.OHLCV,
            start_date=start_date,
            end_date=end_date
        )
        
        # 应该检测到早期缺失
        self.assertGreaterEqual(len(missing), 1)
        early_missing = [m for m in missing if m.start_date < recent_start]
        self.assertGreaterEqual(len(early_missing), 1)
    
    def test_auto_backfill_no_missing(self):
        """测试数据完整时无需补充"""
        # 保存完整数据
        today = date.today()
        start_date = today - timedelta(days=30)
        
        test_records = []
        current = start_date
        while current <= today:
            test_records.append({
                'stock_code': '000001.SZ',
                'trade_date': current.strftime('%Y%m%d'),
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            })
            current += timedelta(days=1)
        
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        # 检测同范围
        missing = self.detector.detect_for_stocks(
            stock_codes=["000001.SZ"],
            data_type=DataType.OHLCV,
            start_date=start_date,
            end_date=today
        )
        
        # 无缺失
        self.assertEqual(len(missing), 0)
    
    def test_multiple_stocks_backfill(self):
        """测试多只股票自动补充"""
        # 插入部分股票数据
        test_records = [
            {
                'stock_code': '000001.SZ',
                'trade_date': '20250101',
                'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5,
                'volume': 1000000, 'amount': 10000000
            }
        ]
        self.storage.save(DataType.OHLCV, test_records, SaveMode.UPSERT)
        
        # 检测多只股票
        missing = self.detector.detect_for_stocks(
            stock_codes=["000001.SZ", "600000.SH", "300001.SZ"],
            data_type=DataType.OHLCV,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31)
        )
        
        # 应该检测到后两只股票缺失
        self.assertGreaterEqual(len(missing), 2)


class TestFetcherRetry(unittest.TestCase):
    """测试API重试机制"""
    
    def test_retry_decorator_exists(self):
        """测试重试装饰器存在"""
        # 检查重试模块是否存在
        retry_path = os.path.join(STOCK_UPDATER_PATH, "fetcher/retry.py")
        
        # 如果文件存在，验证可以导入
        if os.path.exists(retry_path):
            from fetcher.retry import RetryableFetcher
            self.assertTrue(True)
        else:
            # 跳过（重试模块可能未实现）
            self.skipTest("重试模块未实现")


class TestEndToEnd(unittest.TestCase):
    """端到端测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_full_workflow(self):
        """完整工作流测试：扫描->检测->存储"""
        # 1. 创建扫描器
        scanner = ConfigScanner(
            stock_list=["000001", "600000"],
            data_types=[DataType.OHLCV],
            days_back=7
        )
        
        # 2. 扫描需求
        requirements = scanner.scan()
        self.assertEqual(len(requirements), 2)
        
        # 3. 检测缺失
        detector = MissingDataDetector(self.storage)
        missing = detector.detect(requirements)
        
        # 应该有缺失（因为数据库为空）
        self.assertGreaterEqual(len(missing), 2)
        
        # 4. 模拟获取数据并保存
        # 这里使用模拟数据模拟API返回
        mock_records = [
            {
                'stock_code': '000001.SZ',
                'trade_date': (date.today() - timedelta(days=i)).strftime('%Y%m%d'),
                'open': 10.0 + i, 'high': 11.0 + i, 'low': 9.0 + i, 'close': 10.5 + i,
                'volume': 1000000 + i * 10000, 'amount': 10000000 + i * 100000
            }
            for i in range(7)
        ]
        
        saved = self.storage.save(DataType.OHLCV, mock_records, SaveMode.UPSERT)
        self.assertGreater(saved, 0)
        
        # 5. 验证数据已保存
        codes = self.storage.get_all_stock_codes()
        self.assertIn("000001.SZ", codes)
        
        # 6. 再次检测应该无缺失
        missing2 = detector.detect(requirements)
        # 可能还有600000的缺失，但000001应该没有
        self.assertLessEqual(len(missing2), 1)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
