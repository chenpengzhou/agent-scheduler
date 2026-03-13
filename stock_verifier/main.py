# -*- coding: utf-8 -*-
"""
股票数据多源验证模块 - 主入口
"""
import argparse
from datetime import date, timedelta
from .verifier import StockDataVerifier
from .models import VerifyRequest, DataType


def main():
    parser = argparse.ArgumentParser(description='股票数据多源验证模块')
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # verify 命令
    verify_parser = subparsers.add_parser('verify', help='验证数据')
    verify_parser.add_argument('--stock', required=True, help='股票代码')
    verify_parser.add_argument('--date', help='交易日期 (YYYYMMDD)')
    
    # batch 命令
    batch_parser = subparsers.add_parser('batch', help='批量验证')
    batch_parser.add_argument('--stocks', nargs='+', help='股票代码列表')
    batch_parser.add_argument('--days', type=int, default=5, help='验证天数')
    
    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='查看统计')
    
    # reset 命令
    reset_parser = subparsers.add_parser('reset', help='重置被禁用的数据源')
    
    args = parser.parse_args()
    
    # 创建验证器
    verifier = StockDataVerifier()
    
    if args.command == 'verify':
        # 验证单条数据
        stock_code = args.stock
        trade_date = date.today() if not args.date else datetime.strptime(args.date, '%Y%m%d').date()
        
        request = VerifyRequest(
            stock_code=stock_code,
            trade_date=trade_date,
            data_types=[DataType.OHLCV]
        )
        
        print(f"\n开始验证 {stock_code} {trade_date} ...")
        result = verifier.verify(request)
        
        print(f"\n验证结果:")
        print(f"  状态: {result.status.value}")
        print(f"  数据源数: {result.source_count}")
        if result.anomalies:
            print(f"  差异: {result.anomalies}")
        if result.final_data:
            print(f"  最终数据: close={result.final_data.get('close')}")
    
    elif args.command == 'batch':
        # 批量验证
        stock_codes = args.stocks or ['000001.SZ', '600000.SH']
        days = args.days
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        print(f"\n批量验证 {len(stock_codes)} 只股票，近 {days} 天数据...")
        
        requests = []
        for stock_code in stock_codes:
            for d in range(days):
                trade_date = start_date + timedelta(days=d)
                if trade_date.weekday() < 5:  # 跳过周末
                    requests.append(VerifyRequest(
                        stock_code=stock_code,
                        trade_date=trade_date,
                        data_types=[DataType.OHLCV]
                    ))
        
        results = verifier.verify_batch(requests)
        
        print(f"\n验证完成!")
        stats = verifier.get_stats()
        print(f"  总验证: {stats['total']}")
        print(f"  一致: {stats['consistent']}")
        print(f"  不一致: {stats['inconsistent']}")
        print(f"  单源: {stats['single_source']}")
        print(f"  错误: {stats['error']}")
        
        disabled = verifier.get_disabled_sources()
        if disabled:
            print(f"\n⚠️ 被禁用的数据源: {disabled}")
            print(f"   使用 'python -m stock_verifier reset' 重置")
    
    elif args.command == 'stats':
        stats = verifier.get_stats()
        print(f"\n=== 统计信息 ===")
        print(f"总验证: {stats['total']}")
        print(f"一致: {stats['consistent']}")
        print(f"不一致: {stats['inconsistent']}")
        print(f"单源: {stats['single_source']}")
        print(f"错误: {stats['error']}")
        print(f"\n启用的数据源: {stats['enabled_sources']}")
        
        disabled = verifier.get_disabled_sources()
        if disabled:
            print(f"被禁用的数据源: {disabled}")
    
    elif args.command == 'reset':
        verifier.reset_disabled_sources()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    from datetime import datetime
    main()
