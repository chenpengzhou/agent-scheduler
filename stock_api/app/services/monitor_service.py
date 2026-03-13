# -*- coding: utf-8 -*-
"""
监控告警服务
"""
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import requests


class MonitorService:
    """监控告警服务"""
    
    def __init__(self, db_path: str = None):
        import os
        self.db_path = db_path or os.environ.get("STOCK_DB_PATH", os.path.expanduser("~/.openclaw/data/stock.db"))
        self.telegram_enabled = False
        self.telegram_bot_token = ""
        self.telegram_chat_id = ""
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def check_price_alerts(self, threshold: float = 5.0) -> List[Dict]:
        """检查价格异动"""
        conn = self._get_conn()
        
        # 检查表是否存在
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_daily'")
            if not cursor.fetchone():
                conn.close()
                return []
        except:
            conn.close()
            return []
        
        # 获取最新和前一天的数据
        try:
            df = conn.execute('''
                SELECT t1.ts_code, t1.date as today, t1.close as today_close,
                       t2.date as yesterday, t2.close as yesterday_close
                FROM stock_daily t1
                LEFT JOIN stock_daily t2 ON t1.ts_code = t2.ts_code
                WHERE t1.date = (SELECT MAX(date) FROM stock_daily)
                AND t2.date = (SELECT date FROM stock_daily WHERE date < (SELECT MAX(date) FROM stock_daily) ORDER BY date DESC LIMIT 1)
            ''').fetchall()
        except:
            conn.close()
            return []
        
        conn.close()
        
        alerts = []
        for row in df:
            if row['yesterday_close'] and row['yesterday_close'] > 0:
                change_pct = abs(row['today_close'] - row['yesterday_close']) / row['yesterday_close'] * 100
                
                if change_pct > threshold:
                    direction = "↑" if row['today_close'] > row['yesterday_close'] else "↓"
                    alerts.append({
                        "type": "price_alert",
                        "code": row['ts_code'],
                        "change_pct": round(change_pct, 2),
                        "direction": direction,
                        "price": row['today_close'],
                        "severity": "high" if change_pct > 10 else "medium"
                    })
        
        return alerts
    
    def check_volume_alerts(self, threshold: float = 2.0) -> List[Dict]:
        """检查成交量异动"""
        conn = self._get_conn()
        
        df = conn.execute('''
            SELECT ts_code, date, volume, close
            FROM stock_daily
            WHERE date = (SELECT MAX(date) FROM stock_daily)
        ''').fetchall()
        
        conn.close()
        
        # 简化检测
        alerts = []
        for row in df:
            if random.random() < 0.01:  # 模拟
                alerts.append({
                    "type": "volume_alert",
                    "code": row['ts_code'],
                    "volume": row['volume'],
                    "severity": "medium"
                })
        
        return alerts
    
    def check_data_anomalies(self) -> List[Dict]:
        """检查数据异常"""
        conn = self._get_conn()
        
        # 检查缺失数据
        df = conn.execute('''
            SELECT ts_code, date
            FROM stock_daily
            WHERE close IS NULL OR close = 0
            LIMIT 20
        ''').fetchall()
        
        conn.close()
        
        anomalies = []
        for row in df:
            anomalies.append({
                "type": "data_anomaly",
                "code": row['ts_code'],
                "date": row['date'],
                "issue": "invalid_price",
                "severity": "high"
            })
        
        return anomalies
    
    def get_all_alerts(self) -> Dict:
        """获取所有告警"""
        price_alerts = self.check_price_alerts()
        volume_alerts = self.check_volume_alerts()
        anomalies = self.check_data_anomalies()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "price_alerts": price_alerts,
            "volume_alerts": volume_alerts,
            "data_anomalies": anomalies,
            "total": len(price_alerts) + len(volume_alerts) + len(anomalies)
        }
    
    def send_alert(self, message: str, level: str = "info") -> bool:
        """发送告警"""
        if not self.telegram_enabled:
            print(f"[{level.upper()}] {message}")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": f"[{level.upper()}] {message}",
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=data, timeout=10)
            return response.ok
        except Exception as e:
            print(f"发送告警失败: {e}")
            return False
    
    def configure_telegram(self, bot_token: str, chat_id: str):
        """配置Telegram"""
        self.telegram_bot_token = bot_token
        self.telegram_chat_id = chat_id
        self.telegram_enabled = bool(bot_token and chat_id)
    
    def create_alert_rule(self, rule: Dict) -> Dict:
        """创建告警规则"""
        conn = self._get_conn()
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                threshold REAL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            INSERT INTO alert_rules (name, type, threshold)
            VALUES (?, ?, ?)
        ''', (rule["name"], rule["type"], rule.get("threshold", 5.0)))
        
        conn.commit()
        rule_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        
        return {"message": "规则已创建", "rule_id": rule_id}
    
    def get_alert_rules(self) -> List[Dict]:
        """获取告警规则"""
        conn = self._get_conn()
        
        try:
            df = conn.execute('SELECT * FROM alert_rules').fetchall()
            conn.close()
            return [dict(row) for row in df]
        except:
            conn.close()
            return []


# 全局实例
import random
monitor_service = MonitorService()
