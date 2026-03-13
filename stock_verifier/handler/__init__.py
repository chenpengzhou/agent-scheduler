# -*- coding: utf-8 -*-
"""
处理器模块
"""
from abc import ABC, abstractmethod
from typing import Dict
import sqlite3
import os
import json
from datetime import datetime
from ..models import VerifyResult, VerifyStatus, AnomalyRecord, HandleStatus


class ResultHandler(ABC):
    """结果处理器基类"""
    
    @abstractmethod
    def handle(self, result: VerifyResult) -> bool:
        """处理验证结果"""
        pass


class ConsistentHandler(ResultHandler):
    """一致数据处理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def handle(self, result: VerifyResult) -> bool:
        """处理一致数据，直接入库"""
        if not result.final_data:
            return False
        
        # 添加验证元数据
        data = result.final_data.copy()
        data['verify_status'] = 'verified'
        data['verified_at'] = datetime.now().isoformat()
        
        return self._save_to_db(data)
    
    def _save_to_db(self, data: Dict) -> bool:
        """保存到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO stock_daily
                (stock_code, trade_date, open, high, low, close, volume, amount,
                 verify_status, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('stock_code'),
                data.get('trade_date'),
                data.get('open'),
                data.get('high'),
                data.get('low'),
                data.get('close'),
                data.get('volume'),
                data.get('amount'),
                data.get('verify_status'),
                data.get('verified_at')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"⚠️ 保存一致数据失败: {e}")
            return False


class InconsistentHandler(ResultHandler):
    """不一致数据处理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def handle(self, result: VerifyResult) -> bool:
        """处理不一致数据"""
        # 1. 保存异常记录
        anomaly = AnomalyRecord(
            stock_code=result.stock_code,
            trade_date=result.trade_date,
            data_type=result.data_type,
            sources_data=result.sources_data,
            diff_fields=",".join(result.anomalies),
            diff_percentage=max(result.diff_details.values()) if result.diff_details else 0,
            handling_status=HandleStatus.PENDING
        )
        
        self._save_anomaly(anomaly)
        
        # 2. 保存主源数据（带标注）
        if result.final_data:
            data = result.final_data.copy()
            data['verify_status'] = 'inconsistent'
            data['has_anomaly'] = True
            data['verified_at'] = datetime.now().isoformat()
            
            self._save_to_db(data)
        
        # 3. 发送告警
        self._send_alert(result)
        
        return True
    
    def _save_anomaly(self, anomaly: AnomalyRecord) -> bool:
        """保存异常记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_anomaly (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    data_type TEXT,
                    sources_data TEXT,
                    diff_fields TEXT,
                    diff_percentage REAL,
                    handling_status TEXT DEFAULT 'pending',
                    discussion TEXT,
                    resolved_by TEXT,
                    resolved_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO stock_anomaly
                (stock_code, trade_date, data_type, sources_data, diff_fields, 
                 diff_percentage, handling_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                anomaly.stock_code,
                anomaly.trade_date,
                anomaly.data_type,
                json.dumps(anomaly.sources_data),
                anomaly.diff_fields,
                anomaly.diff_percentage,
                anomaly.handling_status.value
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"⚠️ 保存异常记录失败: {e}")
            return False
    
    def _save_to_db(self, data: Dict) -> bool:
        """保存到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO stock_daily
                (stock_code, trade_date, open, high, low, close, volume, amount,
                 verify_status, has_anomaly, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('stock_code'),
                data.get('trade_date'),
                data.get('open'),
                data.get('high'),
                data.get('low'),
                data.get('close'),
                data.get('volume'),
                data.get('amount'),
                data.get('verify_status'),
                data.get('has_anomaly', False),
                data.get('verified_at')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"⚠️ 保存数据失败: {e}")
            return False
    
    def _send_alert(self, result: VerifyResult):
        """发送告警"""
        print(f"🚨 [告警] 数据验证异常: {result.stock_code} {result.trade_date}")
        print(f"   差异字段: {result.anomalies}")
        print(f"   采纳数据源: tushare (最终话语权)")


class SingleSourceHandler(ResultHandler):
    """单源数据处理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def handle(self, result: VerifyResult) -> bool:
        """处理单源数据"""
        if not result.final_data:
            return False
        
        # 标注未验证
        data = result.final_data.copy()
        data['verify_status'] = 'unverified'
        data['verified_at'] = datetime.now().isoformat()
        
        return self._save_to_db(data)
    
    def _save_to_db(self, data: Dict) -> bool:
        """保存到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO stock_daily
                (stock_code, trade_date, open, high, low, close, volume, amount,
                 verify_status, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('stock_code'),
                data.get('trade_date'),
                data.get('open'),
                data.get('high'),
                data.get('low'),
                data.get('close'),
                data.get('volume'),
                data.get('amount'),
                data.get('verify_status'),
                data.get('verified_at')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"⚠️ 保存单源数据失败: {e}")
            return False
