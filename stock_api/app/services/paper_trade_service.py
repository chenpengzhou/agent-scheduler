# -*- coding: utf-8 -*-
"""
模拟交易服务
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime


class PaperTradeService:
    """模拟交易服务"""
    
    def __init__(self, db_path: str = None):
        import os
        self.db_path = db_path or os.path.expanduser("~/.openclaw/data/paper_trade.json")
        self._load_state()
    
    def _load_state(self):
        """加载状态"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    state = json.load(f)
                    self.initial_capital = state.get('initial_capital', 1000000)
                    self.cash = state.get('cash', self.initial_capital)
                    self.positions = state.get('positions', {})
                    self.orders = state.get('orders', [])
                    self.trades = state.get('trades', [])
            except:
                self._init_state()
        else:
            self._init_state()
    
    def _init_state(self):
        """初始化状态"""
        self.initial_capital = 1000000
        self.cash = self.initial_capital
        self.positions = {}
        self.orders = []
        self.trades = []
    
    def _save_state(self):
        """保存状态"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        state = {
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'positions': self.positions,
            'orders': self.orders,
            'trades': self.trades,
            'updated_at': datetime.now().isoformat()
        }
        with open(self.db_path, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    
    def get_positions(self, prices: Dict[str, float] = None) -> List[Dict]:
        """获取所有持仓"""
        result = []
        for code, pos in self.positions.items():
            current_price = prices.get(code, pos['avg_cost']) if prices else pos['avg_cost']
            market_value = pos['quantity'] * current_price
            cost = pos['quantity'] * pos['avg_cost']
            pnl = market_value - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0
            
            result.append({
                'code': code,
                'quantity': pos['quantity'],
                'avg_cost': pos['avg_cost'],
                'current_price': current_price,
                'market_value': round(market_value, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2)
            })
        return result
    
    def get_position(self, code: str) -> Optional[Dict]:
        """获取单个持仓"""
        pos = self.positions.get(code)
        if not pos:
            return None
        return {
            'code': code,
            'quantity': pos['quantity'],
            'avg_cost': pos['avg_cost']
        }
    
    def buy(self, code: str, price: float, quantity: int, date: str = None) -> Dict:
        """买入"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        cost = price * quantity * 1.0003  # 手续费万三
        
        if self.cash < cost:
            return {'success': False, 'error': '资金不足'}
        
        self.cash -= cost
        
        # 更新持仓
        if code in self.positions:
            old_qty = self.positions[code]['quantity']
            old_cost = self.positions[code]['avg_cost']
            new_qty = old_qty + quantity
            new_cost = (old_cost * old_qty + price * quantity) / new_qty
            self.positions[code] = {'quantity': new_qty, 'avg_cost': new_cost}
        else:
            self.positions[code] = {'quantity': quantity, 'avg_cost': price}
        
        # 记录订单
        order_id = len(self.orders) + 1
        self.orders.append({
            'order_id': order_id,
            'date': date,
            'code': code,
            'action': 'buy',
            'price': price,
            'quantity': quantity,
            'status': 'filled'
        })
        
        # 记录成交
        self.trades.append({
            'trade_id': len(self.trades) + 1,
            'date': date,
            'code': code,
            'action': 'buy',
            'price': price,
            'quantity': quantity,
            'amount': round(cost, 2)
        })
        
        self._save_state()
        
        return {
            'success': True,
            'order_id': order_id,
            'cash': round(self.cash, 2)
        }
    
    def sell(self, code: str, price: float, quantity: int, date: str = None) -> Dict:
        """卖出"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        pos = self.positions.get(code)
        if not pos or pos['quantity'] < quantity:
            return {'success': False, 'error': '持仓不足'}
        
        revenue = price * quantity * 0.9997  # 手续费万三
        self.cash += revenue
        
        # 更新持仓
        pos['quantity'] -= quantity
        if pos['quantity'] == 0:
            del self.positions[code]
        
        # 记录订单
        order_id = len(self.orders) + 1
        self.orders.append({
            'order_id': order_id,
            'date': date,
            'code': code,
            'action': 'sell',
            'price': price,
            'quantity': quantity,
            'status': 'filled'
        })
        
        # 记录成交
        self.trades.append({
            'trade_id': len(self.trades) + 1,
            'date': date,
            'code': code,
            'action': 'sell',
            'price': price,
            'quantity': quantity,
            'amount': round(revenue, 2)
        })
        
        self._save_state()
        
        return {
            'success': True,
            'order_id': order_id,
            'cash': round(self.cash, 2)
        }
    
    def get_orders(self, limit: int = 50) -> List[Dict]:
        """获取订单历史"""
        return self.orders[-limit:][::-1]
    
    def get_trades(self, limit: int = 50) -> List[Dict]:
        """获取成交记录"""
        return self.trades[-limit:][::-1]
    
    def get_summary(self, prices: Dict[str, float] = None) -> Dict:
        """获取账户摘要"""
        portfolio_value = 0
        total_cost = 0
        
        for code, pos in self.positions.items():
            current_price = prices.get(code, pos['avg_cost']) if prices else pos['avg_cost']
            market_value = pos['quantity'] * current_price
            cost = pos['quantity'] * pos['avg_cost']
            portfolio_value += market_value
            total_cost += cost
        
        total_value = self.cash + portfolio_value
        total_return = total_value - self.initial_capital
        return_rate = (total_return / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        return {
            'initial_capital': self.initial_capital,
            'cash': round(self.cash, 2),
            'positions_count': len(self.positions),
            'portfolio_value': round(portfolio_value, 2),
            'total_value': round(total_value, 2),
            'total_return': round(total_return, 2),
            'return_rate': round(return_rate, 2),
            'orders_count': len(self.orders),
            'trades_count': len(self.trades)
        }
    
    def reset(self, initial_capital: float = None) -> Dict:
        """重置模拟交易"""
        if initial_capital:
            self.initial_capital = initial_capital
        self.cash = self.initial_capital
        self.positions = {}
        self.orders = []
        self.trades = []
        self._save_state()
        
        return {
            'success': True,
            'initial_capital': self.initial_capital,
            'cash': self.cash
        }


# 全局实例
paper_trade_service = PaperTradeService()
