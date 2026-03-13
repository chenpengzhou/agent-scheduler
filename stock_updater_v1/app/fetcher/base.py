"""数据获取器基类"""
import pandas as pd
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..utils.logger import logger


class DataFetcher(ABC):
    """数据获取器基类"""

    def __init__(self, source_name: str, cache_dir: str = None):
        self.source_name = source_name
        if cache_dir is None:
            cache_dir = f"/tmp/stock_data/{source_name}"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def fetch(self, **kwargs) -> pd.DataFrame:
        """获取数据"""
        pass

    def get_cache_path(self, name: str = "data") -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{name}.parquet"

    def save_cache(self, df: pd.DataFrame, name: str = "data"):
        """保存数据到缓存"""
        cache_path = self.get_cache_path(name)
        df.to_parquet(cache_path)
        logger.debug(f"Saved cache to {cache_path}")

    def load_cache(self, name: str = "data") -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        cache_path = self.get_cache_path(name)
        if cache_path.exists():
            df = pd.read_parquet(cache_path)
            logger.debug(f"Loaded cache from {cache_path}")
            return df
        return None


class GitHubDataFetcher(DataFetcher):
    """GitHub 数据获取器"""

    def __init__(self, source_name: str, repo_url: str, branch: str = "main"):
        super().__init__(source_name)
        self.repo_url = repo_url
        self.branch = branch

    def fetch(self, **kwargs) -> pd.DataFrame:
        """从 GitHub 获取数据"""
        # 这里可以扩展为从 GitHub API 或 raw URL 获取数据
        # 目前作为基类实现
        logger.info(f"Fetching {self.source_name} from GitHub")
        return pd.DataFrame()
