"""AkShare 数据获取器"""
import pandas as pd
from typing import Optional

from .base import DataFetcher
from ..utils.logger import logger


class AkShareFetcher(DataFetcher):
    """AkShare 数据获取器"""

    def __init__(self):
        super().__init__("akshare")
        self._ak = None

    def _init_akshare(self):
        """初始化 akshare"""
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
                logger.info("AkShare initialized successfully")
            except ImportError:
                logger.error("akshare not installed, run: pip install akshare")
                raise

    def fetch_stock_daily(self, symbol: str = "000001", period: str = "daily",
                          start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取 A 股日线数据"""
        self._init_akshare()

        try:
            logger.info(f"Fetching daily data for {symbol}")
            df = self._ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )

            if df is not None and len(df) > 0:
                df['source'] = self.source_name
                df['ts_code'] = symbol
                logger.info(f"Fetched {len(df)} records for {symbol}")
            else:
                logger.warning(f"No data returned for {symbol}")

            return df if df is not None else pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching daily data: {e}")
            return pd.DataFrame()

    def fetch_index_daily(self, symbol: str = "000001") -> pd.DataFrame:
        """获取指数日线数据"""
        self._init_akshare()

        try:
            logger.info(f"Fetching index data for {symbol}")
            df = self._ak.stock_zh_index_daily(symbol=f"sh{symbol}")
            
            if df is not None and len(df) > 0:
                df['source'] = 'index_daily'
                df['ts_code'] = symbol
                logger.info(f"Fetched {len(df)} index records for {symbol}")
            
            return df if df is not None else pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching index data: {e}")
            return pd.DataFrame()

    def fetch_stock_basic(self) -> pd.DataFrame:
        """获取股票基本信息"""
        self._init_akshare()

        try:
            logger.info("Fetching stock basic info")
            df = self._ak.stock_info_a_code_name()
            
            if df is not None and len(df) > 0:
                df['source'] = 'stock_basic'
                logger.info(f"Fetched {len(df)} stock basic records")
            
            return df if df is not None else pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching stock basic: {e}")
            return pd.DataFrame()

    def fetch(self, data_type: str = "daily", **kwargs) -> pd.DataFrame:
        """通用获取接口"""
        if data_type == "daily":
            return self.fetch_stock_daily(**kwargs)
        elif data_type == "index":
            return self.fetch_index_daily(**kwargs)
        elif data_type == "basic":
            return self.fetch_stock_basic()
        else:
            logger.warning(f"Unknown data type: {data_type}")
            return pd.DataFrame()
