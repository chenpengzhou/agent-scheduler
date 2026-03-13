"""Telegram 通知模块"""
import requests
from typing import Dict, Optional
from datetime import datetime

from .config import config
from .utils.logger import logger


class TelegramNotifier:
    """Telegram 通知器"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or config.telegram_bot_token
        self.chat_id = chat_id or config.telegram_chat_id
        self.enabled = config.telegram_enabled and bool(self.bot_token) and bool(self.chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

        if not self.enabled:
            logger.info("Telegram notifications disabled")
        else:
            logger.info("Telegram notifications enabled")

    def _send_request(self, method: str, data: dict) -> bool:
        """发送 API 请求"""
        if not self.enabled or not self.api_url:
            return False

        url = f"{self.api_url}/{method}"
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('ok'):
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return False

        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """发送消息"""
        if not self.enabled:
            logger.debug(f"Telegram disabled, message not sent: {text[:50]}...")
            return False

        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        return self._send_request("sendMessage", data)

    def send_update_success(self, source: str, new_records: int, total_records: int = 0) -> bool:
        """发送更新成功通知"""
        message = f"""
📊 <b>股票数据更新</b>

✅ 更新成功！
- 数据源: {source}
- 新增记录: {new_records}
- 总记录: {total_records if total_records else 'N/A'}
- 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return self.send_message(message.strip())

    def send_update_error(self, source: str, error: str) -> bool:
        """发送更新失败通知"""
        message = f"""
❌ <b>数据更新失败</b>

- 数据源: {source}
- 错误: {error}
- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return self.send_message(message.strip())

    def send_startup(self) -> bool:
        """发送启动通知"""
        message = f"""
🚀 <b>股票数据更新模块启动</b>

- 版本: V1.0
- 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return self.send_message(message.strip())

    def send_shutdown(self) -> bool:
        """发送关闭通知"""
        message = f"""
🛑 <b>股票数据更新模块关闭</b>

- 关闭时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return self.send_message(message.strip())

    def test(self) -> bool:
        """测试连接"""
        if not self.enabled:
            logger.warning("Telegram not enabled")
            return False

        message = "✅ 测试消息 - 股票数据更新模块"
        return self.send_message(message)


# 全局通知器实例
notifier = TelegramNotifier()
