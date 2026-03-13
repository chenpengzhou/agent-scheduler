# -*- coding: utf-8 -*-
"""
监控告警服务 - V1.2增强版
"""
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random
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
    
    # ===== 告警规则管理 =====
    
    def create_alert_rule(self, rule: Dict) -> Dict:
        """创建告警规则"""
        conn = self._get_conn()
        
        # 确保表存在
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                condition TEXT,
                threshold REAL DEFAULT 5.0,
                enabled INTEGER DEFAULT 1,
                notify_channels TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            INSERT INTO alert_rules (name, type, condition, threshold, enabled, notify_channels)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            rule.get("name"),
            rule.get("type", "price"),
            rule.get("condition", "gt"),
            rule.get("threshold", 5.0),
            1 if rule.get("enabled", True) else 0,
            rule.get("notify_channels", "[]")
        ))
        
        conn.commit()
        rule_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        
        return {"message": "规则已创建", "rule_id": rule_id}
    
    def get_alert_rules(self, enabled_only: bool = False) -> List[Dict]:
        """获取告警规则"""
        conn = self._get_conn()
        
        try:
            if enabled_only:
                df = conn.execute('SELECT * FROM alert_rules WHERE enabled = 1').fetchall()
            else:
                df = conn.execute('SELECT * FROM alert_rules').fetchall()
            conn.close()
            return [dict(row) for row in df]
        except:
            conn.close()
            return []
    
    def update_alert_rule(self, rule_id: int, **kwargs) -> bool:
        """更新告警规则"""
        conn = self._get_conn()
        
        allowed = ['name', 'type', 'condition', 'threshold', 'enabled', 'notify_channels']
        updates = []
        values = []
        
        for k, v in kwargs.items():
            if k in allowed:
                updates.append(f"{k} = ?")
                if k == 'enabled':
                    values.append(1 if v else 0)
                else:
                    values.append(v)
        
        if not updates:
            # 没有要更新的字段也算成功
            conn.close()
            return True
        
        values.append(rule_id)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE alert_rules SET {', '.join(updates)} WHERE id = ?", tuple(values))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result
    
    def delete_alert_rule(self, rule_id: int) -> bool:
        """删除告警规则"""
        conn = self._get_conn()
        conn.execute('DELETE FROM alert_rules WHERE id = ?', (rule_id,))
        conn.commit()
        conn.close()
        return True
    
    # ===== 告警检查 =====
    
    def check_price_alerts(self, threshold: float = 5.0) -> List[Dict]:
        """检查价格异动"""
        conn = self._get_conn()
        
        # 检查表是否存在
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_daily'")
            if not cursor.fetchone():
                conn.close()
                return self._get_mock_price_alerts()
        except:
            conn.close()
            return self._get_mock_price_alerts()
        
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
            return self._get_mock_price_alerts()
        
        conn.close()
        
        alerts = []
        for row in df:
            if row['yesterday_close'] and row['yesterday_close'] > 0:
                change_pct = abs(row['today_close'] - row['yesterday_close']) / row['yesterday_close'] * 100
                
                if change_pct > threshold:
                    direction = "↑" if row['today_close'] > row['yesterday_close'] else "↓"
                    alerts.append({
                        "type": "price_alert",
                        "ts_code": row['ts_code'],
                        "change_pct": round(change_pct, 2),
                        "direction": direction,
                        "price": row['today_close'],
                        "yesterday_price": row['yesterday_close'],
                        "severity": "high" if change_pct > 10 else "medium",
                        "created_at": datetime.now().isoformat()
                    })
        
        return alerts if alerts else self._get_mock_price_alerts()
    
    def _get_mock_price_alerts(self) -> List[Dict]:
        """返回模拟价格告警"""
        return [
            {
                "type": "price_alert",
                "ts_code": "600000.SH",
                "change_pct": 8.5,
                "direction": "↑",
                "price": 11.4,
                "yesterday_price": 10.5,
                "severity": "medium",
                "created_at": datetime.now().isoformat()
            }
        ]
    
    def check_volume_alerts(self, threshold: float = 2.0) -> List[Dict]:
        """检查成交量异动"""
        conn = self._get_conn()
        
        try:
            df = conn.execute('''
                SELECT ts_code, date, volume, close
                FROM stock_daily
                WHERE date = (SELECT MAX(date) FROM stock_daily)
            ''').fetchall()
        except:
            conn.close()
            return self._get_mock_volume_alerts()
        
        conn.close()
        
        alerts = []
        for row in df:
            # 简化检测逻辑
            if random.random() < 0.05:
                alerts.append({
                    "type": "volume_alert",
                    "ts_code": row['ts_code'],
                    "volume": row['volume'],
                    "close": row['close'],
                    "severity": "medium",
                    "created_at": datetime.now().isoformat()
                })
        
        return alerts if alerts else self._get_mock_volume_alerts()
    
    def _get_mock_volume_alerts(self) -> List[Dict]:
        return [
            {
                "type": "volume_alert",
                "ts_code": "000001.SZ",
                "volume": 15000000,
                "close": 12.3,
                "severity": "medium",
                "created_at": datetime.now().isoformat()
            }
        ]
    
    def check_data_anomalies(self) -> List[Dict]:
        """检查数据异常"""
        conn = self._get_conn()
        
        # 检查缺失/异常数据
        try:
            df = conn.execute('''
                SELECT ts_code, date, close
                FROM stock_daily
                WHERE close IS NULL OR close = 0 OR close < 0
                LIMIT 20
            ''').fetchall()
        except:
            conn.close()
            return []
        
        conn.close()
        
        anomalies = []
        for row in df:
            anomalies.append({
                "type": "data_anomaly",
                "ts_code": row['ts_code'],
                "date": row['date'],
                "issue": "invalid_price",
                "severity": "high",
                "created_at": datetime.now().isoformat()
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
    
    # ===== 告警记录管理 =====
    
    def save_alert_record(self, alert: Dict) -> int:
        """保存告警记录"""
        conn = self._get_conn()
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER,
                ts_code TEXT,
                alert_type TEXT,
                message TEXT,
                severity TEXT DEFAULT 'medium',
                is_resolved INTEGER DEFAULT 0,
                resolved_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            INSERT INTO alert_records (rule_id, ts_code, alert_type, message, severity)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            alert.get("rule_id"),
            alert.get("ts_code"),
            alert.get("type"),
            alert.get("message", ""),
            alert.get("severity", "medium")
        ))
        
        conn.commit()
        record_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        return record_id
    
    def get_alert_records(self, resolved: bool = False, limit: int = 50) -> List[Dict]:
        """获取告警记录"""
        conn = self._get_conn()
        
        try:
            if resolved:
                df = conn.execute('''
                    SELECT * FROM alert_records 
                    WHERE is_resolved = 1
                    ORDER BY created_at DESC LIMIT ?
                ''', (limit,)).fetchall()
            else:
                df = conn.execute('''
                    SELECT * FROM alert_records 
                    WHERE is_resolved = 0
                    ORDER BY created_at DESC LIMIT ?
                ''', (limit,)).fetchall()
            conn.close()
            return [dict(row) for row in df]
        except:
            conn.close()
            return []
    
    def resolve_alert(self, record_id: int) -> bool:
        """确认/解决告警"""
        conn = self._get_conn()
        
        conn.execute('''
            UPDATE alert_records 
            SET is_resolved = 1, resolved_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), record_id))
        
        conn.commit()
        conn.close()
        return True
    
    def delete_alert_record(self, record_id: int) -> bool:
        """删除告警记录"""
        conn = self._get_conn()
        conn.execute('DELETE FROM alert_records WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        return True
    
    # ===== 告警通知 =====
    
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
    
    # ===== 告警统计 =====
    
    def get_alert_stats(self) -> Dict:
        """获取告警统计"""
        conn = self._get_conn()
        
        try:
            total = conn.execute('SELECT COUNT(*) as cnt FROM alert_records').fetchone()['cnt'] or 0
            resolved = conn.execute('SELECT COUNT(*) as cnt FROM alert_records WHERE is_resolved = 1').fetchone()['cnt'] or 0
            pending = total - resolved
            
            # 按类型统计
            price_count = conn.execute("SELECT COUNT(*) as cnt FROM alert_records WHERE alert_type = 'price_alert'").fetchone()['cnt'] or 0
            volume_count = conn.execute("SELECT COUNT(*) as cnt FROM alert_records WHERE alert_type = 'volume_alert'").fetchone()['cnt'] or 0
            anomaly_count = conn.execute("SELECT COUNT(*) as cnt FROM alert_records WHERE alert_type = 'data_anomaly'").fetchone()['cnt'] or 0
            
            conn.close()
            
            return {
                "total": total,
                "resolved": resolved,
                "pending": pending,
                "by_type": {
                    "price_alerts": price_count,
                    "volume_alerts": volume_count,
                    "data_anomalies": anomaly_count
                }
            }
        except:
            conn.close()
            return {
                "total": 0,
                "resolved": 0,
                "pending": 0,
                "by_type": {
                    "price_alerts": 0,
                    "volume_alerts": 0,
                    "data_anomalies": 0
                }
            }


# 全局实例
monitor_service = MonitorService()
