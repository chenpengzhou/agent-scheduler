# -*- coding: utf-8 -*-
"""
数据同步服务 - 支持增量更新、错误重试、日志记录
"""
import sqlite3
import pandas as pd
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import os

# 配置日志
LOG_DIR = os.path.expanduser("~/.openclaw/logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/stock_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StockSyncService:
    """数据同步服务"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get("STOCK_DB_PATH", os.path.expanduser("~/.openclaw/data/stock.db"))
        self.is_running = False
        self.max_workers = 4
        self.retry_times = 3
        self.retry_delay = 5  # 秒
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM sync_tasks ORDER BY id DESC LIMIT 1")
            task = cursor.fetchone()
            conn.close()
            
            if task:
                return {
                    "status": task["status"],
                    "total_stocks": task["total_stocks"],
                    "completed_stocks": task["completed_stocks"],
                    "current_stock": task["current_stock"],
                    "started_at": task["started_at"],
                    "progress": round(task["completed_stocks"] / task["total_stocks"] * 100, 2) if task["total_stocks"] else 0
                }
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            conn.close()
        
        return {"status": "idle", "total_stocks": 0, "completed_stocks": 0}
    
    def start_sync(self, force_full: bool = False) -> Dict:
        """启动同步"""
        if self.is_running:
            return {"message": "同步已在运行中", "status": "running"}
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 获取股票列表
        try:
            cursor.execute("SELECT DISTINCT ts_code FROM stock_info")
            stock_list = [row['ts_code'] for row in cursor.fetchall()]
        except:
            stock_list = self._get_default_stock_list()
        
        # 获取需要同步的股票
        if force_full:
            stocks_to_sync = stock_list
        else:
            stocks_to_sync = self._get_stocks_need_sync()
        
        total = len(stocks_to_sync)
        now = datetime.now().isoformat()
        
        # 插入新任务
        cursor.execute('''
            INSERT INTO sync_tasks (status, total_stocks, completed_stocks, started_at)
            VALUES (?, ?, ?, ?)
        ''', ("running", total, 0, now))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # 启动后台同步
        self.is_running = True
        self._run_sync_task(task_id, stocks_to_sync)
        
        logger.info(f"同步任务已启动, 任务ID: {task_id}, 股票数: {total}")
        
        return {"message": "同步已启动", "task_id": task_id, "total": total}
    
    def _run_sync_task(self, task_id: int, stocks: List[str]):
        """后台执行同步任务"""
        import threading
        
        thread = threading.Thread(target=self._sync_worker, args=(task_id, stocks))
        thread.daemon = True
        thread.start()
    
    def _sync_worker(self, task_id: int, stocks: List[str]):
        """同步工作线程"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        completed = 0
        failed = []
        
        for stock in stocks:
            if not self.is_running:
                logger.info("同步被中断")
                break
            
            try:
                # 模拟数据获取（实际应该调用 akshare 等数据源）
                data = self._fetch_stock_data(stock)
                
                if data is not None and not data.empty:
                    # 写入数据库
                    self._save_stock_data(conn, stock, data)
                    completed += 1
                    
                    # 更新进度
                    cursor.execute('''
                        UPDATE sync_tasks 
                        SET completed_stocks = ?, current_stock = ?
                        WHERE id = ?
                    ''', (completed, stock, task_id))
                    conn.commit()
                    
                    logger.info(f"同步成功: {stock} ({completed}/{len(stocks)})")
                else:
                    failed.append(stock)
                    logger.warning(f"获取数据失败: {stock}")
                    
            except Exception as e:
                failed.append(stock)
                logger.error(f"同步失败: {stock}, 错误: {e}")
        
        # 完成任务
        cursor.execute('''
            UPDATE sync_tasks 
            SET status = ?, completed_stocks = ?, stopped_at = ?
            WHERE id = ?
        ''', ("completed" if not failed else "failed", completed, datetime.now().isoformat(), task_id))
        conn.commit()
        conn.close()
        
        self.is_running = False
        logger.info(f"同步任务完成. 成功: {completed}, 失败: {len(failed)}")
    
    def _fetch_stock_data(self, ts_code: str, retry: int = 3) -> Optional[pd.DataFrame]:
        """获取股票数据（带重试和多数据源自动切换）"""
        # 按优先级尝试各数据源
        sources = [
            ("tushare", self._fetch_from_tushare),
            ("akshare", self._fetch_from_akshare),
            ("baostock", self._fetch_from_baostock),
        ]
        
        last_error = None
        for source_name, fetch_func in sources:
            for attempt in range(retry):
                try:
                    data = fetch_func(ts_code)
                    if data is not None and not data.empty:
                        logger.info(f"从 {source_name} 获取数据成功: {ts_code}")
                        return data
                except Exception as e:
                    last_error = e
                    logger.warning(f"从 {source_name} 获取数据失败 (尝试 {attempt + 1}/{retry}): {ts_code}, {e}")
                    if attempt < retry - 1:
                        time.sleep(self.retry_delay)
            
            logger.warning(f"{source_name} 数据源不可用，尝试下一个数据源...")
        
        logger.error(f"所有数据源均失败: {ts_code}, 最后错误: {last_error}")
        return None
    
    def _fetch_from_tushare(self, ts_code: str) -> Optional[pd.DataFrame]:
        """从 Tushare 获取数据"""
        token = os.environ.get("TUSHARE_TOKEN")
        if not token:
            logger.warning("TUSHARE_TOKEN 环境变量未设置")
            return None
        
        import tushare as ts
        
        pro = ts.pro_api(token)
        
        # 获取最近30个交易日的数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=35)).strftime('%Y%m%d')
        
        # 先获取日线数据
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df is None or df.empty:
            return None
        
        # 重命名字段以匹配数据库结构
        df = df.rename(columns={
            'trade_date': 'date',
            'vol': 'volume'
        })
        
        # 确保日期格式一致
        df['date'] = df['date'].astype(str)
        
        return df
    
    def _fetch_from_akshare(self, ts_code: str) -> Optional[pd.DataFrame]:
        """从 Akshare 获取数据"""
        import akshare as ak
        
        # 转换代码格式: 600000.SH -> 600000
        code = ts_code.split('.')[0]
        market = ts_code.split('.')[1].lower()  # sh 或 sz
        
        # 使用 akshare 的股票历史数据接口
        if market == 'sh':
            symbol = f"sh{code}"
        else:
            symbol = f"sz{code}"
        
        try:
            # 获取日线数据
            df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                    start_date=(datetime.now() - timedelta(days=35)).strftime('%Y%m%d'),
                                    end_date=datetime.now().strftime('%Y%m%d'))
            
            if df is None or df.empty:
                return None
            
            # 重命名字段
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_change',
            })
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
            
            # 添加 ts_code
            df['ts_code'] = ts_code
            
            # 只保留需要的字段
            fields = ['ts_code', 'date', 'open', 'high', 'low', 'close', 'volume']
            for f in fields:
                if f not in df.columns:
                    df[f] = None
            
            return df[fields]
            
        except Exception as e:
            logger.warning(f"akshare 获取失败: {ts_code}, {e}")
            return None
    
    def _fetch_from_baostock(self, ts_code: str) -> Optional[pd.DataFrame]:
        """从 Baostock 获取数据"""
        import baostock as bs
        
        bs.login()
        
        try:
            # 转换代码格式: 600000.SH -> sh.600000
            code = ts_code.split('.')[0]
            market = ts_code.split('.')[1].lower()
            bs_code = f"{market}.{code}"
            
            start_date = (datetime.now() - timedelta(days=35)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount,turnover_rate",
                start_date=start_date,
                end_date=end_date,
                frequency="d"
            )
            
            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return None
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 重命名字段
            df = df.rename(columns={
                'code': 'ts_code_original',
            })
            
            # 添加 ts_code
            df['ts_code'] = ts_code
            
            # 转换数值字段
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover_rate']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 格式化日期
            df['date'] = df['date'].str.replace('-', '')
            
            # 只保留需要的字段
            fields = ['ts_code', 'date', 'open', 'high', 'low', 'close', 'volume']
            for f in fields:
                if f not in df.columns:
                    df[f] = None
            
            return df[fields]
            
        finally:
            bs.logout()
    
    def _save_stock_data(self, conn, ts_code: str, data: pd.DataFrame):
        """保存股票数据"""
        cursor = conn.cursor()
        
        for _, row in data.iterrows():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_daily 
                    (ts_code, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['ts_code'],
                    row['date'],
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ))
            except Exception as e:
                logger.error(f"保存数据失败: {ts_code}, {e}")
        
        conn.commit()
    
    def _get_stocks_need_sync(self) -> List[str]:
        """获取需要同步的股票（增量更新）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 获取已有数据的股票
        try:
            cursor.execute("SELECT DISTINCT ts_code FROM stock_daily")
            existing = set(row['ts_code'] for row in cursor.fetchall())
        except:
            existing = set()
        
        # 获取所有股票
        try:
            cursor.execute("SELECT DISTINCT ts_code FROM stock_info")
            all_stocks = [row['ts_code'] for row in cursor.fetchall()]
        except:
            all_stocks = self._get_default_stock_list()
        
        conn.close()
        
        # 返回需要同步的股票（新增或需要更新的）
        return [s for s in all_stocks if s not in existing or self._need_update(s)]
    
    def _need_update(self, ts_code: str) -> bool:
        """检查是否需要更新"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT MAX(date) as latest FROM stock_daily 
                WHERE ts_code = ?
            ''', (ts_code,))
            row = cursor.fetchone()
            
            if row and row['latest']:
                latest_date = datetime.strptime(row['latest'], '%Y%m%d')
                # 如果最新数据超过1天，需要更新
                return (datetime.now() - latest_date).days > 1
        except:
            pass
        
        conn.close()
        return True
    
    def _get_default_stock_list(self) -> List[str]:
        """获取默认股票列表"""
        return [
            "600000.SH", "600036.SH", "600519.SH", "601318.SH",
            "000001.SZ", "000002.SZ", "000333.SZ", "600030.SH",
            "601166.SH", "600016.SH"
        ]
    
    def stop_sync(self) -> Dict:
        """停止同步"""
        self.is_running = False
        logger.info("同步已停止请求")
        return {"message": "同步已停止"}
    
    def get_sync_logs(self, limit: int = 100) -> List[Dict]:
        """获取同步日志"""
        try:
            with open(f"{LOG_DIR}/stock_sync.log", "r") as f:
                lines = f.readlines()
                return [{"time": l.split(" - ")[0], "level": l.split(" - ")[1], "message": l.split(" - ", 2)[2].strip() if len(l.split(" - ")) > 2 else ""} for l in lines[-limit:]]
        except:
            return []


# 全局实例
sync_service = StockSyncService()
