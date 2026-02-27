#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
假数据清理清单
记录所有被清理的假数据代码
"""

CLEANUP_SUMMARY = {
    "清理日期": "2025-02-22",
    "清理范围": "/home/robin/github/ 下所有 Python 文件",
    
    "假数据类型": {
        "1. 财务指标假数据": "np.random.uniform 生成 ROE/利润率等",
        "2. 估值指标假数据": "np.random.uniform 生成 PE/PB 等",
        "3. 技术指标假数据": "random.uniform/choice 生成 RSI/MACD 等",
        "4. 股价假数据": "random.uniform 生成买卖价格",
        "5. 收益假数据": "random.uniform 生成涨跌幅",
        "6. 模拟股票数据": "np.random.randn 生成价格序列",
    },
    
    "已清理文件": [
        # commodity-monitor 项目
        "commodity-monitor/scripts/strategies/quality/quality_selector.py",
        "commodity-monitor/scripts/strategies/quality/quality_backtest.py",
        "commodity-monitor/scripts/strategies/quality/tune_quality.py",
        "commodity-monitor/scripts/strategies/value/value_selector.py",
        "commodity-monitor/scripts/strategies/value/value_backtest.py",
        "commodity-monitor/scripts/strategies/value/tune_value.py",
        "commodity-monitor/scripts/strategies/momentum/tune_momentum.py",
        "commodity-monitor/scripts/strategies/report_non_bull.py",
        "commodity-monitor/scripts/strategies/full_report.py",
        "commodity-monitor/scripts/commodity_monitor.py",
        "commodity-monitor/scripts/full_selection.py",
        "commodity-monitor/scripts/backtest_2020.py",
        "commodity-monitor/scripts/backtest_quarterly.py",
        "commodity-monitor/scripts/bear_market_backtest_2022.py",
        "commodity-monitor/scripts/bear_market_backtest_2018.py",
        "commodity-monitor/scripts/bear_market_backtest_2011.py",
        "commodity-monitor/scripts/bear_neutral_test.py",
        "commodity-monitor/scripts/backtest.py",
        "commodity-monitor/scripts/market_type.py",
        "commodity-monitor/src/factors/factor_momentum.py",
        "commodity-monitor/src/factors/factor_profit_trend.py",
        "commodity-monitor/src/factors/factor_profit_volatility.py",
        "commodity-monitor/src/factors/factor_revenue_volatility.py",
        
        # a-stock-monitor 项目
        "a-stock-monitor/quant_strategies/scripts/backtest_2020.py",
        "a-stock-monitor/quant_strategies/scripts/backtest.py",
        "a-stock-monitor/quant_strategies/scripts/backtest_quarterly.py",
        "a-stock-monitor/quant_strategies/scripts/commodity_monitor.py",
        "a-stock-monitor/quant_strategies/scripts/full_selection.py",
        "a-stock-monitor/quant_strategies/scripts/market_type.py",
        "a-stock-monitor/quant_strategies/strategies/bull_strategy/modules/growth.py",
        "a-stock-monitor/quant_strategies/strategies/bull_strategy/modules/sector_rotation.py",
        "a-stock-monitor/quant_strategies/strategies/bull_strategy/modules/trend.py",
        "a-stock-monitor/quant_strategies/strategies/momentum_strategy/momentum/momentum_backtest.py",
        "a-stock-monitor/quant_strategies/strategies/momentum_strategy/momentum/tune_momentum.py",
        "a-stock-monitor/src/factors/factor_profit_trend.py",
        "a-stock-monitor/src/factors/factor_profit_volatility.py",
        "a-stock-monitor/src/factors/factor_revenue_volatility.py",
        
        # crypto-monitor 项目
        "crypto-monitor/scripts/monitor_base.py",
    ],
    
    "处理方式": {
        "方式1-删除": "删除纯模拟的测试代码和假数据函数",
        "方式2-替换": "替换为从真实 API 获取数据",
        "方式3-注释": "标记 TODO 待接入真实数据源",
        "方式4-保留": "保留非股票数据的 random 使用（如调参搜索）",
    },
    
    "清理原则": [
        "1. 所有股票数据必须来自 Tushare/BaoStock API",
        "2. 所有数据必须存入本地 SQLite 缓存",
        "3. 禁止任何 random 生成股票数据",
        "4. 保留 random 的合法用途（如参数调优的组合生成）",
    ]
}

if __name__ == '__main__':
    import json
    print(json.dumps(CLEANUP_SUMMARY, indent=2, ensure_ascii=False))
