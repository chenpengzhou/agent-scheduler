"""数据校验模块"""
import pandas as pd
from typing import Dict, List, Any

from .utils.logger import logger


class DataValidator:
    """数据校验器"""

    def __init__(self):
        self.required_fields = {
            'daily': ['ts_code', 'date', 'open', 'high', 'low', 'close', 'volume'],
            'basic': ['ts_code', 'name'],
            'index': ['ts_code', 'date', 'open', 'high', 'low', 'close']
        }

    def validate(self, df: pd.DataFrame, data_type: str = 'daily') -> Dict[str, Any]:
        """校验数据"""
        if df is None or len(df) == 0:
            return {
                "valid": False,
                "errors": ["Empty DataFrame"],
                "warnings": [],
                "row_count": 0
            }

        errors = []
        warnings = []

        # 1. 检查必需字段
        field_errors = self._check_required_fields(df, data_type)
        errors.extend(field_errors)

        # 2. 检查数据范围
        range_errors = self._check_data_range(df)
        errors.extend(range_errors)

        # 3. 检查数据完整性
        completeness_warnings = self._check_completeness(df)
        warnings.extend(completeness_warnings)

        # 4. 检查数据一致性
        consistency_errors = self._check_consistency(df)
        errors.extend(consistency_errors)

        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "row_count": len(df),
            "columns": list(df.columns)
        }

        if not result["valid"]:
            logger.warning(f"Validation failed: {errors}")
        elif warnings:
            logger.info(f"Validation passed with warnings: {warnings}")

        return result

    def _check_required_fields(self, df: pd.DataFrame, data_type: str) -> List[str]:
        """检查必需字段"""
        errors = []
        required = self.required_fields.get(data_type, [])

        for field in required:
            if field not in df.columns:
                errors.append(f"Missing required field: {field}")

        return errors

    def _check_data_range(self, df: pd.DataFrame) -> List[str]:
        """检查数据范围"""
        errors = []

        # 检查价格是否为正数
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                invalid = df[df[col] <= 0]
                if len(invalid) > 0:
                    errors.append(f"Invalid {col} price (<=0): {len(invalid)} rows")

        # 检查最高价 >= 最低价
        if 'high' in df.columns and 'low' in df.columns:
            invalid = df[df['high'] < df['low']]
            if len(invalid) > 0:
                errors.append(f"Invalid high < low: {len(invalid)} rows")

        # 检查最高价 >= 开盘价和收盘价
        if 'high' in df.columns:
            for col in ['open', 'close']:
                if col in df.columns:
                    invalid = df[df['high'] < df[col]]
                    if len(invalid) > 0:
                        errors.append(f"Invalid high < {col}: {len(invalid)} rows")

        # 检查最低价 <= 开盘价和收盘价
        if 'low' in df.columns:
            for col in ['open', 'close']:
                if col in df.columns:
                    invalid = df[df['low'] > df[col]]
                    if len(invalid) > 0:
                        errors.append(f"Invalid low > {col}: {len(invalid)} rows")

        # 检查成交量是否为负
        if 'volume' in df.columns:
            invalid = df[df['volume'] < 0]
            if len(invalid) > 0:
                errors.append(f"Invalid volume (<0): {len(invalid)} rows")

        return errors

    def _check_completeness(self, df: pd.DataFrame) -> List[str]:
        """检查数据完整性"""
        warnings = []

        # 检查缺失值比例
        for col in df.columns:
            null_ratio = df[col].isnull().sum() / len(df)
            if null_ratio > 0.1:  # 超过10%缺失
                warnings.append(f"High null ratio in {col}: {null_ratio:.1%}")

        return warnings

    def _check_consistency(self, df: pd.DataFrame) -> List[str]:
        """检查数据一致性"""
        errors = []

        # 检查日期格式
        if 'date' in df.columns:
            try:
                pd.to_datetime(df['date'], errors='raise')
            except:
                errors.append("Invalid date format")

        return errors

    def validate_and_raise(self, df: pd.DataFrame, data_type: str = 'daily'):
        """校验并抛出异常"""
        result = self.validate(df, data_type)
        if not result["valid"]:
            raise ValueError(f"Validation failed: {result['errors']}")
        return result
