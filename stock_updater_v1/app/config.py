"""配置管理模块"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List


class Config:
    """配置管理类"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # 默认使用项目根目录的 config.yaml
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config.yaml"

        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not Path(self.config_path).exists():
            return self._default_config()

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            'updater': {
                'sources': [
                    {'name': 'akshare', 'enabled': True, 'interval': 60, 'priority': 1},
                    {'name': 'stock_basic', 'enabled': True, 'interval': 3600, 'priority': 2},
                ],
                'database': {
                    'path': '/home/robin/.openclaw/data/stock.db'
                },
                'telegram': {
                    'enabled': False,
                    'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
                    'chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
                },
                'scheduler': {
                    'check_interval': 60,
                    'max_retries': 3,
                    'retry_delay': 300
                }
            }
        }

    @property
    def sources(self) -> List[Dict]:
        """获取数据源配置"""
        return self._config.get('updater', {}).get('sources', [])

    @property
    def database_path(self) -> str:
        """获取数据库路径"""
        return self._config.get('updater', {}).get('database', {}).get(
            'path', '/home/robin/.openclaw/data/stock.db'
        )

    @property
    def telegram_enabled(self) -> bool:
        """是否启用 Telegram 通知"""
        return self._config.get('updater', {}).get('telegram', {}).get('enabled', False)

    @property
    def telegram_bot_token(self) -> str:
        """Telegram Bot Token"""
        return self._config.get('updater', {}).get('telegram', {}).get('bot_token', '')

    @property
    def telegram_chat_id(self) -> str:
        """Telegram Chat ID"""
        return self._config.get('updater', {}).get('telegram', {}).get('chat_id', '')

    @property
    def check_interval(self) -> int:
        """调度器检查间隔（秒）"""
        return self._config.get('updater', {}).get('scheduler', {}).get('check_interval', 60)

    @property
    def max_retries(self) -> int:
        """最大重试次数"""
        return self._config.get('updater', {}).get('scheduler', {}).get('max_retries', 3)

    @property
    def retry_delay(self) -> int:
        """重试延迟（秒）"""
        return self._config.get('updater', {}).get('scheduler', {}).get('retry_delay', 300)

    def get_source_config(self, source_name: str) -> Dict:
        """获取指定数据源配置"""
        for source in self.sources:
            if source.get('name') == source_name:
                return source
        return {}


# 全局配置实例
config = Config()
