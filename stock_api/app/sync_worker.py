# -*- coding: utf-8 -*-
"""
后台同步任务
"""
import threading
import time
import sqlite3
from datetime import datetime
from typing import Optional, List
import os


class SyncWorker:
    """同步工作器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """启动同步任务"""
        if self.running:
            return False
        
        self.running = True
        self._thread = threading.Thread(target=self._run_sync, daemon=True)
        self._thread.start()
        return True
    
    def stop(self):
        """停止同步任务"""
        self.running = False
    
    def is_running(self) -> bool:
        return self.running
    
    def _run_sync(self):
        """执行同步"""
        print("[SyncWorker] 开始同步任务...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 获取当前任务
            cursor.execute("SELECT * FROM sync_tasks WHERE status = 'running' ORDER BY id DESC LIMIT 1")
            task = cursor.fetchone()
            
            if not task:
                print("[SyncWorker] 无运行中的任务")
                self.running = False
                return
            
            task_id = task['id']
            total_stocks = task['total_stocks']
            
            # 获取要同步的股票列表
            stock_list = self._get_stock_list(cursor)
            
            if not stock_list:
                # 如果没有股票，随机生成测试数据
                stock_list = [f"{str(i).zfill(6)}.SH" if i % 2 == 0 else f"{str(i).zfill(6)}.SZ" 
                             for i in range(600000, 600050)]
            
            completed = 0
            
            for i, stock_code in enumerate(stock_list):
                if not self.running:
                    break
                
                try:
                    # 获取数据
                    data = self._fetch_stock_data(stock_code)
                    
                    if data:
                        # 保存到数据库
                        self._save_stock_data(cursor, stock_code, data)
                    
                    completed += 1
                    
                    # 更新进度
                    progress = int(completed / len(stock_list) * 100)
                    cursor.execute('''
                        UPDATE sync_tasks 
                        SET completed_stocks = ?, current_stock = ?
                        WHERE id = ?
                    ''', (completed, stock_code, task_id))
                    
                    conn.commit()
                    
                    # 每10个股票输出一次日志
                    if completed % 10 == 0:
                        print(f"[SyncWorker] 进度: {completed}/{len(stock_list)} ({progress}%)")
                    
                    # 模拟网络延迟
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"[SyncWorker] 处理 {stock_code} 失败: {e}")
                    continue
            
            # 完成任务
            if self.running:
                cursor.execute('''
                    UPDATE sync_tasks 
                    SET status = 'completed', completed_stocks = ?
                    WHERE id = ?
                ''', (completed, task_id))
                print(f"[SyncWorker] 同步完成: {completed} 条")
            else:
                cursor.execute('''
                    UPDATE sync_tasks 
                    SET status = 'stopped', completed_stocks = ?
                    WHERE id = ?
                ''', (completed, task_id))
                print(f"[SyncWorker] 同步停止: {completed} 条")
            
            conn.commit()
            
        except Exception as e:
            print(f"[SyncWorker] 同步出错: {e}")
        
        finally:
            conn.close()
            self.running = False
            print("[SyncWorker] 同步任务结束")
    
    def _get_stock_list(self, cursor) -> List[str]:
        """获取股票列表"""
        try:
            cursor.execute("SELECT DISTINCT ts_code FROM stock_daily LIMIT 100")
            return [row['ts_code'] for row in cursor.fetchall()]
        except:
            return []
    
    def _fetch_stock_data(self, stock_code: str) -> Optional[dict]:
        """获取股票数据（模拟）"""
        import random
        import math
        
        # 生成模拟数据
        base_price = random.uniform(5, 50)
        
        return {
            "date": datetime.now().strftime("%Y%m%d"),
            "open": round(base_price * random.uniform(0.98, 1.02), 2),
            "high": round(base_price * random.uniform(1.00, 1.05), 2),
            "low": round(base_price * random.uniform(0.95, 1.00), 2),
            "close": round(base_price, 2),
            "volume": random.randint(1000000, 100000000),
            "amount": random.uniform(10000000, 1000000000)
        }
    
    def _save_stock_data(self, cursor, stock_code: str, data: dict):
        """保存股票数据"""
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO stock_daily
                (ts_code, date, open, high, low, close, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stock_code,
                data["date"],
                data["open"],
                data["high"],
                data["low"],
                data["close"],
                data["volume"],
                data["amount"]
            ))
        except Exception as e:
            print(f"[SyncWorker] 保存失败: {e}")


# 全局同步工作器
_sync_worker: Optional[SyncWorker] = None


def get_sync_worker(db_path: str = None) -> SyncWorker:
    """获取同步工作器实例"""
    global _sync_worker
    if _sync_worker is None:
        db_path = db_path or os.environ.get("STOCK_DB_PATH", "/home/deploy/.openclaw/data/stock.db")
        _sync_worker = SyncWorker(db_path)
    return _sync_worker
