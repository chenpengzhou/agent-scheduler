"""数据清洗模块"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List

from .utils.logger import logger


class DataCleaner:
    """数据清洗器"""

    def __init__(self):
        self.default_fill_values = {
            'open': 0.0,
            'high': 0.0,
            'low': 0.0,
            'close': 0.0,
            'volume': 0.0,
            'amount': 0.0
        }

    def clean(self, df: pd.DataFrame, source: str = None) -> pd.DataFrame:
        """清洗数据"""
        if df is None or len(df) == 0:
            logger.warning("Empty DataFrame, skipping clean")
            return df

        original_count = len(df)
        logger.info(f"Cleaning data for source: {source}, original rows: {original_count}")

        # 1. 删除重复行
        df = self._remove_duplicates(df)

        # 2. 处理缺失值
        df = self._handle_missing_values(df)

        # 3. 类型转换
        df = self._convert_types(df)

        # 4. 数据校验过滤
        df = self._filter_invalid_data(df)

        # 5. 排序
        df = self._sort_data(df)

        logger.info(f"Cleaned data: {original_count} -> {len(df)} rows")
        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """删除重复行"""
        before = len(df)
        df = df.drop_duplicates()
        if before > len(df):
            logger.debug(f"Removed {before - len(df)} duplicate rows")
        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        # 填充数值列的缺失值
        for col, fill_value in self.default_fill_values.items():
            if col in df.columns:
                df[col] = df[col].fillna(fill_value)

        # 删除关键列全为空的行
        key_cols = ['date', 'ts_code', 'close']
        existing_key_cols = [c for c in key_cols if c in df.columns]
        if existing_key_cols:
            df = df.dropna(subset=existing_key_cols, how='all')

        return df

    def _convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """类型转换"""
        # 日期列转换
        date_cols = ['date', 'trade_date', 'update_date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df[col] = df[col].dt.strftime('%Y-%m-%d')

        # 数值列转换
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def _filter_invalid_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """过滤无效数据"""
        # 过滤价格为负或零的行
        if 'close' in df.columns:
            before = len(df)
            df = df[df['close'] > 0]
            if before > len(df):
                logger.debug(f"Filtered {before - len(df)} rows with invalid close price")

        # 过滤日期为空的行
        if 'date' in df.columns:
            before = len(df)
            df = df[df['date'].notna()]
            if before > len(df):
                logger.debug(f"Filtered {before - len(df)} rows with null date")

        return df

    def _sort_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """排序数据"""
        sort_cols = []
        if 'ts_code' in df.columns:
            sort_cols.append('ts_code')
        if 'date' in df.columns:
            sort_cols.append('date')

        if sort_cols:
            df = df.sort_values(sort_cols).reset_index(drop=True)

        return df

    def clean_stock_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗股票日线数据"""
        return self.clean(df, source='stock_daily')

    def clean_stock_basic(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗股票基本信息"""
        if df is None or len(df) == 0:
            return df

        # 重命名列
        rename_map = {
            '代码': 'ts_code',
            '名称': 'name',
            '行业': 'industry',
            '上市日期': 'list_date'
        }
        df = df.rename(columns=rename_map)

        return self.clean(df, source='stock_basic')
