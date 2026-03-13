# -*- coding: utf-8 -*-
"""
股票数据更新模块 - 主入口
"""
import argparse
import sys
from datetime import date, timedelta
from .updater import StockDataUpdater
from .config import get_config
from .utils import setup_logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股票数据更新模块')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # sync 命令 - 同步数据
    sync_parser = subparsers.add_parser('sync', help='同步数据')
    sync_parser.add_argument('--stocks', nargs='+', help='股票代码列表')
    sync_parser.add_argument('--days', type=int, help='回溯天数')
    sync_parser.add_argument('--config', type=str, help='配置文件路径')
    
    # backfill 命令 - 补历史数据
    backfill_parser = subparsers.add_parser('backfill', help='补历史数据')
    backfill_parser.add_argument('--stocks', nargs='+', help='股票代码列表')
    backfill_parser.add_argument('--max-days', type=int, help='最大补数据天数')
    backfill_parser.add_argument('--config', type=str, help='配置文件路径')
    
    # scan 命令 - 仅扫描
    scan_parser = subparsers.add_parser('scan', help='扫描数据需求')
    scan_parser.add_argument('--config', type=str, help='配置文件路径')
    
    # stats 命令 - 查看统计
    stats_parser = subparsers.add_parser('stats', help='查看统计信息')
    stats_parser.add_argument('--config', type=str, help='配置文件路径')
    
    # test 命令 - 测试连接
    test_parser = subparsers.add_parser('test', help='测试 API 连接')
    test_parser.add_argument('--config', type=str, help='配置文件路径')
    
    args = parser.parse_args()
    
    # 设置日志
    config = get_config(args.config if hasattr(args, 'config') else None)
    setup_logger(level=config.logging.level, log_file=config.logging.file)
    
    # 创建更新器
    updater = StockDataUpdater(config_path=args.config if hasattr(args, 'config') and args.config else None)
    
    # 执行命令
    if args.command == 'sync':
        result = updater.sync_for_strategy(
            stock_codes=args.stocks,
            days_back=args.days
        )
        print(f"\n结果: {result}")
        
    elif args.command == 'backfill':
        result = updater.auto_backfill(
            stock_codes=args.stocks,
            max_days=args.max_days
        )
        print(f"\n结果: {result}")
        
    elif args.command == 'scan':
        requirements = updater.scan_requirements()
        print(f"\n扫描到 {len(requirements)} 条数据需求")
        for req in requirements[:10]:
            print(f"  - {req.stock_code}: {req.start_date} ~ {req.end_date}")
        if len(requirements) > 10:
            print(f"  ... 还有 {len(requirements) - 10} 条")
        
    elif args.command == 'stats':
        stats = updater.get_stats()
        print(f"\n=== 统计信息 ===")
        print(f"扫描需求: {stats['scan_count']}")
        print(f"缺失数据: {stats['missing_count']}")
        print(f"获取记录: {stats['fetch_count']}")
        print(f"保存记录: {stats['save_count']}")
        print(f"\n=== 数据库统计 ===")
        db_stats = stats.get('db_stats', {})
        print(f"日线数据: {db_stats.get('daily_count', 0)} 条")
        print(f"股票数量: {db_stats.get('daily_stocks', 0)} 只")
        print(f"数据范围: {db_stats.get('daily_range', (None, None))}")
        
    elif args.command == 'test':
        result = updater.test_connection()
        if result:
            print("✅ API 连接正常")
        else:
            print("❌ API 连接失败")
            sys.exit(1)
    
    else:
        # 默认执行 sync
        result = updater.sync_for_strategy()
        print(f"\n结果: {result}")


if __name__ == '__main__':
    main()
