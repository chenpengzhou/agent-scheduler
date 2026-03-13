"""主入口模块"""
import sys
import signal
import argparse
from datetime import datetime

from .config import config
from .scheduler import scheduler
from .storage import storage
from .notifier import notifier
from .fetcher.akshare_fetcher import AkShareFetcher
from .cleaner import DataCleaner
from .validator import DataValidator
from .utils.logger import logger


class StockUpdaterApp:
    """股票数据更新应用"""

    def __init__(self):
        self.running = False
        self.fetcher = AkShareFetcher()
        self.cleaner = DataCleaner()
        self.validator = DataValidator()

    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def init_database(self):
        """初始化数据库"""
        logger.info("Initializing database...")
        storage.init_tables()

    def register_jobs(self):
        """注册定时任务"""
        for source_config in config.sources:
            if not source_config.get('enabled', True):
                continue

            source_name = source_config['name']
            interval = source_config.get('interval', 60)

            if source_name == 'akshare':
                scheduler.add_job(
                    f"fetch_{source_name}",
                    self.job_fetch_akshare_daily,
                    interval
                )
            elif source_name == 'stock_basic':
                scheduler.add_job(
                    f"fetch_{source_name}",
                    self.job_fetch_stock_basic,
                    interval
                )

        logger.info(f"Registered {len(scheduler.jobs)} jobs")

    def job_fetch_akshare_daily(self):
        """获取 A 股日线数据任务"""
        logger.info("Starting job: fetch_akshare_daily")
        start_time = datetime.now()

        try:
            # 获取上证指数日线数据
            df = self.fetcher.fetch(data_type="index", symbol="000001")

            if df is not None and len(df) > 0:
                # 清洗数据
                df_cleaned = self.cleaner.clean(df, source='index_daily')

                # 校验数据
                validation = self.validator.validate(df_cleaned, 'index')
                if not validation['valid']:
                    logger.warning(f"Validation warnings: {validation['errors']}")

                # 保存数据
                storage.replace(df_cleaned, 'stock_daily')

                # 记录日志
                storage.log_update(
                    source='akshare_daily',
                    status='success',
                    records=len(df_cleaned),
                    message=f"Updated {len(df_cleaned)} records"
                )

                # 发送通知
                notifier.send_update_success(
                    source='akshare_daily',
                    new_records=len(df_cleaned),
                    total_records=storage.get_table_count('stock_daily')
                )

                logger.info(f"Job completed: {len(df_cleaned)} records saved")
            else:
                logger.warning("No data fetched")

        except Exception as e:
            logger.error(f"Job failed: {e}")
            storage.log_update(source='akshare_daily', status='error', records=0, message=str(e))
            notifier.send_update_error('akshare_daily', str(e))

        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Job duration: {elapsed:.2f}s")

    def job_fetch_stock_basic(self):
        """获取股票基本信息任务"""
        logger.info("Starting job: fetch_stock_basic")
        start_time = datetime.now()

        try:
            df = self.fetcher.fetch(data_type="basic")

            if df is not None and len(df) > 0:
                # 清洗数据
                df_cleaned = self.cleaner.clean_stock_basic(df)

                # 校验数据
                validation = self.validator.validate(df_cleaned, 'basic')
                if not validation['valid']:
                    logger.warning(f"Validation warnings: {validation['errors']}")

                # 保存数据
                storage.replace(df_cleaned, 'stock_basic')

                # 记录日志
                storage.log_update(
                    source='stock_basic',
                    status='success',
                    records=len(df_cleaned),
                    message=f"Updated {len(df_cleaned)} records"
                )

                # 发送通知
                notifier.send_update_success(
                    source='stock_basic',
                    new_records=len(df_cleaned),
                    total_records=storage.get_table_count('stock_basic')
                )

                logger.info(f"Job completed: {len(df_cleaned)} records saved")
            else:
                logger.warning("No data fetched")

        except Exception as e:
            logger.error(f"Job failed: {e}")
            storage.log_update(source='stock_basic', status='error', records=0, message=str(e))
            notifier.send_update_error('stock_basic', str(e))

        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Job duration: {elapsed:.2f}s")

    def run(self, background: bool = False):
        """运行应用"""
        self.running = True
        self.setup_signal_handlers()

        logger.info("=" * 50)
        logger.info("Stock Data Updater V1.0 Starting")
        logger.info("=" * 50)

        # 初始化数据库
        self.init_database()

        # 注册任务
        self.register_jobs()

        # 发送启动通知
        notifier.send_startup()

        if background:
            scheduler.start_background()
            logger.info("Running in background")
        else:
            # 运行一次任务
            logger.info("Running jobs once for testing...")
            self.job_fetch_akshare_daily()
            logger.info("Test run completed. Use --background to run as daemon.")

    def stop(self):
        """停止应用"""
        self.running = False
        scheduler.stop()
        notifier.send_shutdown()
        logger.info("Stock Data Updater Stopped")
        sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Stock Data Updater V1.0")
    parser.add_argument('--background', '-b', action='store_true', help='Run in background')
    parser.add_argument('--once', action='store_true', help='Run jobs once and exit')
    args = parser.parse_args()

    app = StockUpdaterApp()

    if args.once:
        # 单次运行
        app.init_database()
        app.job_fetch_akshare_daily()
    else:
        # 守护进程模式
        app.run(background=args.background)

        # 保持主线程运行
        try:
            import time
            while app.running:
                time.sleep(1)
        except KeyboardInterrupt:
            app.stop()


if __name__ == "__main__":
    main()
