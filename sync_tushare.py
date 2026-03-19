#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare数据同步脚本
使用方法:
    python sync_tushare.py [token]
    或设置环境变量: TUSHARE_TOKEN
"""
import os
import sys
import sqlite3
import pandas as pd
import logging
from datetime import datetime, timedelta

# 配置日志
LOG_DIR = os.path.expanduser("~/.openclaw/logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/tushare_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = os.path.expanduser("~/.openclaw/data/stock.db")


def get_tushare(token: str):
    """获取Tushare连接"""
    try:
        import tushare as ts
        pro = ts.pro_api(token)
        logger.info("Tushare连接成功")
        return pro
    except Exception as e:
        logger.error(f"Tushare连接失败: {e}")
        return None


def get_last_trade_date(pro):
    """获取最近有交易的日期"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM stock_daily")
        last_date = cursor.fetchone()[0]
        conn.close()
        
        if last_date:
            # Tushare需要从下一个交易日开始
            from datetime import datetime
            last_dt = datetime.strptime(last_date, '%Y%m%d')
            # 跳过周末
            days_to_add = 1
            if last_dt.weekday() == 4:  # 周五
                days_to_add = 3
            elif last_dt.weekday() == 5:  # 周六
                days_to_add = 2
            next_date = last_dt + timedelta(days=days_to_add)
            return next_date.strftime('%Y%m%d')
        return (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
    except Exception as e:
        logger.warning(f"获取最后交易日期失败: {e}")
        return (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')


def sync_stock_daily(pro, trade_date: str):
    """同步股票日线数据"""
    try:
        # 获取A股所有股票
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
        
        synced = 0
        failed = 0
        
        for _, row in df.iterrows():
            ts_code = row['ts_code']
            try:
                # 获取日线数据
                daily_df = pro.daily(ts_code=ts_code, start_date=trade_date, end_date=trade_date)
                
                if daily_df is not None and not daily_df.empty:
                    # 写入数据库
                    conn = sqlite3.connect(DB_PATH)
                    daily_df.to_sql('stock_daily', conn, if_exists='append', index=False)
                    conn.close()
                    synced += 1
                    logger.info(f"同步成功: {ts_code}")
                else:
                    logger.warning(f"无数据: {ts_code}")
                    
            except Exception as e:
                failed += 1
                logger.error(f"同步失败: {ts_code}, {e}")
        
        return synced, failed
        
    except Exception as e:
        logger.error(f"同步失败: {e}")
        return 0, 0


def sync_index_daily(pro, trade_date: str):
    """同步指数数据"""
    try:
        indices = ['000001.SH', '399001.SZ', '399006.SZ', '000300.SH', '000016.SH']
        
        for index_code in indices:
            try:
                df = pro.index_daily(ts_code=index_code, start_date=trade_date, end_date=trade_date)
                if df is not None and not df.empty:
                    conn = sqlite3.connect(DB_PATH)
                    df.to_sql('stock_daily', conn, if_exists='append', index=False)
                    conn.close()
                    logger.info(f"指数同步成功: {index_code}")
            except Exception as e:
                logger.error(f"指数同步失败: {index_code}, {e}")
                
    except Exception as e:
        logger.error(f"指数同步失败: {e}")


def main():
    """主函数"""
    # 获取Token
    token = os.environ.get('TUSHARE_TOKEN') or (sys.argv[1] if len(sys.argv) > 1 else None)
    
    if not token:
        logger.error("请设置TUSHARE_TOKEN环境变量或提供Token参数")
        print("使用方法:")
        print("  python sync_tushare.py <your_tushare_token>")
        print("  或设置环境变量: export TUSHARE_TOKEN=your_token")
        sys.exit(1)
    
    logger.info(f"开始同步数据, Token: {token[:10]}...")
    
    # 连接Tushare
    pro = get_tushare(token)
    if not pro:
        sys.exit(1)
    
    # 获取起始日期（最近有交易的日期）
    start_date = get_last_trade_date(pro)
    today = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"同步日期范围: {start_date} - {today}")
    
    # 同步股票日线数据
    synced, failed = sync_stock_daily(pro, start_date)
    logger.info(f"股票同步完成: 成功 {synced}, 失败 {failed}")
    
    # 同步指数数据
    sync_index_daily(pro, start_date)
    
    logger.info("数据同步完成!")


if __name__ == '__main__':
    main()
