# -*- coding: utf-8 -*-
"""
数据管理服务
"""
import sqlite3
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.utils.db import get_stock_connection, query_one, query_all, execute
import os


class DataManager:
    """数据管理服务"""
    
    def __init__(self, db_path: str = None):
        import os
        self.db_path = db_path or os.environ.get("STOCK_DB_PATH", os.path.expanduser("~/.openclaw/data/stock.db"))
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 尝试从tasks表获取
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
        except:
            pass
        
        conn.close()
        return {"status": "idle", "total_stocks": 0, "completed_stocks": 0}
    
    def start_sync(self) -> Dict:
        """启动同步"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 获取股票数量
        try:
            cursor.execute("SELECT COUNT(DISTINCT ts_code) as cnt FROM stock_daily")
            total = cursor.fetchone()["cnt"]
        except:
            total = 5000
        
        now = datetime.now().isoformat()
        
        # 插入新任务
        cursor.execute('''
            INSERT INTO sync_tasks (status, total_stocks, started_at)
            VALUES (?, ?, ?)
        ''', ("running", total, now))
        
        conn.commit()
        task_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        
        return {"message": "同步已启动", "task_id": task_id}
    
    def stop_sync(self) -> Dict:
        """停止同步"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE sync_tasks SET status = ?, stopped_at = ?
            WHERE status = 'running'
        ''', ("stopped", now))
        
        conn.commit()
        conn.close()
        
        return {"message": "同步已停止"}
    
    def get_quality_report(self) -> Dict:
        """获取数据质量报告"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        report = {}
        
        # 总记录数
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM stock_daily")
            report["total_records"] = cursor.fetchone()["cnt"]
        except:
            report["total_records"] = 0
        
        # 股票数量
        try:
            cursor.execute("SELECT COUNT(DISTINCT ts_code) as cnt FROM stock_daily")
            report["stock_count"] = cursor.fetchone()["cnt"]
        except:
            report["stock_count"] = 0
        
        # 数据完整性
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM stock_daily WHERE close IS NULL OR close = 0")
            invalid = cursor.fetchone()["cnt"]
            report["invalid_records"] = invalid
            report["valid_rate"] = round((report["total_records"] - invalid) / report["total_records"] * 100, 2) if report["total_records"] else 0
        except:
            report["invalid_records"] = 0
            report["valid_rate"] = 0
        
        # 日期范围
        try:
            cursor.execute("SELECT MIN(date) as min_date, MAX(date) as max_date FROM stock_daily")
            row = cursor.fetchone()
            report["date_range"] = {"start": row["min_date"], "end": row["max_date"]}
        except:
            report["date_range"] = {"start": None, "end": None}
        
        conn.close()
        return report
    
    def manual_backfill(self, stock_code: str, start_date: str = None, end_date: str = None) -> Dict:
        """手动补数据"""
        # 模拟补数据
        return {
            "message": f"手动补数据任务已创建",
            "stock_code": stock_code,
            "start_date": start_date,
            "end_date": end_date
        }
    
    def export_data(self, format: str = "csv", stocks: List[str] = None) -> str:
        """导出数据"""
        conn = self._get_conn()
        
        query = "SELECT * FROM stock_daily"
        params = []
        
        if stocks:
            placeholders = ','.join(['?'] * len(stocks))
            query += f" WHERE ts_code IN ({placeholders})"
            params = stocks
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        # 导出
        export_dir = "/tmp/stock_exports"
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "csv":
            filepath = f"{export_dir}/stock_data_{timestamp}.csv"
            df.to_csv(filepath, index=False)
        elif format == "excel":
            filepath = f"{export_dir}/stock_data_{timestamp}.xlsx"
            df.to_excel(filepath, index=False)
        else:
            filepath = f"{export_dir}/stock_data_{timestamp}.json"
            df.to_json(filepath, orient="records")
        
        return filepath


# 全局实例
data_manager = DataManager()
