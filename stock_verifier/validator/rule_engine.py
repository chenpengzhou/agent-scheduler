# -*- coding: utf-8 -*-
"""
验证规则引擎
"""
from typing import Dict, Optional, List
from ..models import (
    VerifyResult, VerifyStatus, FieldType, HandlerType,
    SOURCE_PRIORITY
)
from ..models.rule import VerifyRule, DEFAULT_RULES


class RuleEngine:
    """验证规则引擎"""
    
    def __init__(self, rules: List[VerifyRule] = None):
        self.rules = rules or DEFAULT_RULES
    
    def verify(self,
                sources_data: Dict[str, Optional[Dict]],
                stock_code: str,
                trade_date: str,
                data_type: str) -> VerifyResult:
        """
        执行验证
        
        Args:
            sources_data: {数据源: 数据}
            stock_code: 股票代码
            trade_date: 交易日期
            data_type: 数据类型
            
        Returns:
            验证结果
        """
        result = VerifyResult(
            stock_code=stock_code,
            trade_date=trade_date,
            data_type=data_type,
            sources_data=sources_data
        )
        
        # 统计有效数据源
        valid_sources = {k: v for k, v in sources_data.items() if v is not None}
        
        if not valid_sources:
            result.status = VerifyStatus.ERROR
            result.anomalies.append("所有数据源获取失败")
            return result
        
        if len(valid_sources) == 1:
            # 单源数据
            result.status = VerifyStatus.SINGLE_SOURCE
            result.final_data = list(valid_sources.values())[0]
            return result
        
        # 多源数据验证
        self._verify_multiple_sources(result, valid_sources)
        
        return result
    
    def _verify_multiple_sources(self, 
                                  result: VerifyResult,
                                  valid_sources: Dict[str, Dict]):
        """验证多源数据"""
        # 获取所有需要验证的字段
        all_fields = set()
        for data in valid_sources.values():
            all_fields.update(data.keys())
        
        # 排除非数值字段
        numeric_fields = {'open', 'high', 'low', 'close', 'volume', 'amount'}
        fields_to_check = all_fields & numeric_fields
        
        # 按字段验证
        inconsistent_fields = []
        
        for field in fields_to_check:
            values = {}
            for source, data in valid_sources.items():
                val = data.get(field)
                if val is not None and val != 0:
                    values[source] = val
            
            if len(values) < 2:
                continue
            
            # 找到主源作为参考
            primary_value = None
            for source in SOURCE_PRIORITY:
                if source.value in values:
                    primary_value = values[source.value]
                    break
            
            if primary_value is None:
                continue
            
            # 计算差异
            for source, value in values.items():
                diff_pct = abs(value - primary_value) / primary_value
                result.diff_details[f"{source}.{field}"] = diff_pct
                
                # 查找对应规则
                rule = self._find_rule(field)
                if rule and diff_pct > rule.threshold:
                    inconsistent_fields.append(
                        f"{field}: {diff_pct:.2%} (vs {list(values.keys())[0]})"
                    )
        
        # 判断最终状态
        if inconsistent_fields:
            result.status = VerifyStatus.INCONSISTENT
            result.anomalies = inconsistent_fields
            
            # 少数服从多数 + Tushare最终话语权
            result.final_data = self._resolve_by_majority(
                valid_sources, result.diff_details
            )
        else:
            result.status = VerifyStatus.CONSISTENT
            # 信任 Tushare（主源）
            if 'tushare' in valid_sources:
                result.final_data = valid_sources['tushare']
            else:
                result.final_data = list(valid_sources.values())[0]
    
    def _find_rule(self, field: str) -> Optional[VerifyRule]:
        """查找字段对应的规则"""
        for rule in self.rules:
            if rule.field == field:
                return rule
        return None
    
    def _resolve_by_majority(self,
                             valid_sources: Dict[str, Dict],
                             diff_details: Dict[str, float]) -> Dict:
        """
        少数服从多数，Tushare有最终话语权
        
        逻辑：
        1. 如果 Tushare 数据与多数一致，信任 Tushare
        2. 如果 Tushare 与多数不一致，信任 Tushare（最终话语权）
        3. 否则使用加权平均
        """
        # 简单实现：信任 Tushare
        if 'tushare' in valid_sources:
            return valid_sources['tushare']
        
        # 次选：按权重
        weighted_sum = {}
        weights = {}
        
        for source, data in valid_sources.items():
            w = self._get_weight(source)
            weights[source] = w
            
            for field, value in data.items():
                if field in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                    if field not in weighted_sum:
                        weighted_sum[field] = 0
                    weighted_sum[field] += value * w
        
        # 计算加权平均
        total_weight = sum(weights.values())
        if total_weight > 0:
            result = {}
            for field, total in weighted_sum.items():
                result[field] = total / total_weight
            return result
        
        return list(valid_sources.values())[0]
    
    def _get_weight(self, source: str) -> float:
        """获取数据源权重"""
        weights = {
            'tushare': 0.40,
            '聚宽': 0.30,
            'baostock': 0.20,
            'akshare': 0.10
        }
        return weights.get(source, 0.0)
