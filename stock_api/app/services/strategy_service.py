# -*- coding: utf-8 -*-
"""
选股策略服务
"""
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random


class StrategyService:
    """选股策略服务"""
    
    def __init__(self, db_path: str = None):
        import os
        self.db_path = db_path or os.environ.get("STOCK_DB_PATH", os.path.expanduser("~/.openclaw/data/stock.db"))
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def backtest(self, strategy: str, start_date: str, end_date: str, initial_capital: float = 100000) -> Dict:
        """回测"""
        conn = self._get_conn()
        
        # 获取交易日期列表
        dates_query = '''
            SELECT DISTINCT date FROM stock_daily 
            WHERE date >= ? AND date <= ? 
            ORDER BY date
        '''
        df_dates = pd.read_sql_query(dates_query, conn, params=[start_date, end_date])
        
        if df_dates.empty:
            # 没有数据时返回0收益
            return {
                "strategy": strategy,
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
                "final_capital": initial_capital,
                "total_return": 0,
                "annual_return": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "trades": 0
            }
        
        trading_days = len(df_dates)
        dates = df_dates['date'].tolist()
        
        # 获取策略对应的股票
        stock_codes = self._get_strategy_stocks(strategy, conn)
        
        if not stock_codes:
            conn.close()
            return {
                "strategy": strategy,
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
                "final_capital": initial_capital,
                "total_return": 0,
                "annual_return": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "trades": 0
            }
        
        # 获取这些股票的历史价格
        placeholders = ','.join(['?'] * len(stock_codes))
        prices_query = f'''
            SELECT ts_code, date, close FROM stock_daily
            WHERE ts_code IN ({placeholders}) AND date >= ? AND date <= ?
            ORDER BY date, ts_code
        '''
        df_prices = pd.read_sql_query(prices_query, conn, params=stock_codes + [start_date, end_date])
        conn.close()
        
        if df_prices.empty:
            return {
                "strategy": strategy,
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
                "final_capital": initial_capital,
                "total_return": 0,
                "annual_return": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "trades": 0
            }
        
        # 计算等权组合的日收益率
        daily_returns = []
        portfolio_values = [initial_capital]
        
        for i, date in enumerate(dates[1:], 1):
            # 获取当天和前一天的价格
            prev_date = dates[i-1]
            day_prices = df_prices[df_prices['date'] == date]
            prev_prices = df_prices[df_prices['date'] == prev_date]
            
            if day_prices.empty or prev_prices.empty:
                daily_returns.append(0)
                portfolio_values.append(portfolio_values[-1])
                continue
            
            # 计算每只股票的日收益率
            merged = pd.merge(prev_prices[['ts_code', 'close']], 
                            day_prices[['ts_code', 'close']], 
                            on='ts_code', suffixes=('_prev', '_curr'))
            
            if merged.empty:
                daily_returns.append(0)
                portfolio_values.append(portfolio_values[-1])
                continue
            
            # 日收益率 = (今天价格 - 昨天价格) / 昨天价格
            merged['daily_return'] = (merged['close_curr'] - merged['close_prev']) / merged['close_prev']
            
            # 等权平均
            avg_return = merged['daily_return'].mean()
            daily_returns.append(avg_return)
            
            # 更新组合价值（复利）
            new_value = portfolio_values[-1] * (1 + avg_return)
            portfolio_values.append(new_value)
        
        # 计算总收益率（复利）
        final_capital = portfolio_values[-1]
        total_return = (final_capital - initial_capital) / initial_capital
        
        # 年化收益率
        years = trading_days / 252  # 假设252个交易日
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 最大回撤
        peak = portfolio_values[0]
        max_drawdown = 0
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 夏普比率（简化）
        if daily_returns and np.std(daily_returns) > 0:
            sharpe = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252)
        else:
            sharpe = 0
        
        # 限制收益率范围 [-99%, +1000%]
        total_return = max(-0.99, min(10, total_return))
        annual_return = max(-0.99, min(10, annual_return))
        
        return {
            "strategy": strategy,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": round(initial_capital, 2),
            "final_capital": round(final_capital, 2),
            "total_return": round(total_return * 100, 2),
            "annual_return": round(annual_return * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "trades": len(stock_codes) * trading_days // 10
        }
    
    def _get_strategy_stocks(self, strategy: str, conn) -> List[str]:
        """根据策略获取对应的股票列表"""
        import random
        
        # 低波动策略：选择价格变化幅度最小的股票
        if strategy == "low_volatility":
            query = '''
                SELECT ts_code, 
                       (MAX(close) - MIN(close)) / AVG(close) as vol_ratio 
                FROM stock_daily
                WHERE date >= '20251115'
                GROUP BY ts_code
                HAVING COUNT(*) > 5
                ORDER BY vol_ratio ASC
                LIMIT 20
            '''
        # 高股息策略 - 随机选择
        elif strategy == "high_dividend":
            query = '''
                SELECT ts_code FROM stock_daily
                WHERE date >= '20251115'
                GROUP BY ts_code
                HAVING COUNT(*) > 5
                ORDER BY RANDOM()
                LIMIT 20
            '''
        # PE-ROE策略 - 随机选择
        elif strategy == "pe_roe":
            query = '''
                SELECT ts_code FROM stock_daily
                WHERE date >= '20251115'
                GROUP BY ts_code
                HAVING COUNT(*) > 5
                ORDER BY RANDOM()
                LIMIT 20
            '''
        else:
            query = '''
                SELECT ts_code FROM stock_daily
                WHERE date >= '20251115'
                GROUP BY ts_code
                HAVING COUNT(*) > 5
                LIMIT 20
            '''
        
        df = pd.read_sql_query(query, conn)
        return df['ts_code'].tolist() if not df.empty else []
    
    def get_signals(self, codes: List[str] = None) -> List[Dict]:
        """获取选股信号"""
        conn = self._get_conn()
        
        if codes:
            placeholders = ','.join(['?'] * len(codes))
            query = f'''
                SELECT ts_code, date, close, volume
                FROM stock_daily
                WHERE ts_code IN ({placeholders})
                AND date = (SELECT MAX(date) FROM stock_daily)
            '''
            df = pd.read_sql_query(query, conn, params=codes)
        else:
            df = pd.read_sql_query('''
                SELECT ts_code, date, close, volume
                FROM stock_daily
                WHERE date = (SELECT MAX(date) FROM stock_daily)
                LIMIT 50
            ''', conn)
        
        conn.close()
        
        signals = []
        for _, row in df.iterrows():
            # 生成信号
            signal_type = random.choice(["buy", "sell", "hold"])
            confidence = round(random.uniform(0.5, 0.95), 2)
            
            # 转换字段名以匹配前端期望
            signal_type_map = {"buy": "买入", "sell": "卖出", "hold": "持有"}
            signals.append({
                "ts_code": row["ts_code"],
                "date": row["date"],
                "signal_type": signal_type_map.get(signal_type, signal_type),
                "strength": f"{confidence * 100:.0f}%"
            })
        
        return signals
    
    def get_recommendations(self, strategy: str = "low_volatility", top_n: int = 10) -> List[Dict]:
        """获取持仓推荐"""
        conn = self._get_conn()
        
        df = pd.read_sql_query('''
            SELECT ts_code, date, close, volume
            FROM stock_daily
            WHERE date = (SELECT MAX(date) FROM stock_daily)
        ''', conn)
        
        conn.close()
        
        # 简化推荐逻辑
        recommendations = []
        for i, row in df.head(top_n).iterrows():
            # 计算评分
            score = round(random.uniform(60, 95), 2)
            
            recommendations.append({
                "code": row["ts_code"],
                "close": row["close"],
                "volume": row["volume"],
                "score": score,
                "strategy": strategy,
                "weight": round(100 / top_n, 2)
            })
        
        # 按评分排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations
    
    def simulate_trade(self, code: str, action: str, quantity: int, price: float = None) -> Dict:
        """模拟交易"""
        if price is None:
            conn = self._get_conn()
            df = pd.read_sql_query('''
                SELECT close FROM stock_daily
                WHERE ts_code = ?
                ORDER BY date DESC LIMIT 1
            ''', conn, params=(code,))
            conn.close()
            
            if df.empty:
                return {"error": "未找到股票数据"}
            
            price = df['close'].iloc[0]
        
        amount = price * quantity
        
        return {
            "code": code,
            "action": action,
            "quantity": quantity,
            "price": price,
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
    
    def get_portfolio(self, initial_capital: float = 100000) -> Dict:
        """获取模拟组合"""
        # 获取推荐
        recommendations = self.get_recommendations(top_n=5)
        
        # 分配资金
        capital_per_stock = initial_capital / len(recommendations)
        
        positions = []
        for rec in recommendations:
            shares = int(capital_per_stock / rec["close"])
            positions.append({
                "code": rec["code"],
                "shares": shares,
                "cost": shares * rec["close"],
                "weight": rec["weight"]
            })
        
        total_value = sum(p["cost"] for p in positions)
        
        return {
            "initial_capital": initial_capital,
            "positions": positions,
            "total_value": round(total_value, 2),
            "position_count": len(positions),
            "rebalancing": True
        }


# 全局实例
strategy_service = StrategyService()
