"""
日志配置 - structlog
"""
import logging
import sys
from pathlib import Path
import structlog
from structlog.stdlib import LoggerFactory


def setup_logging(level: str = "INFO", log_file: str = None, format: str = "json"):
    """配置日志系统"""
    
    # 确保日志目录存在
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置标准日志
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # 配置structlog
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()


# 全局logger
logger = None


def get_logger(name: str = None):
    """获取logger"""
    global logger
    if logger is None:
        logger = setup_logging()
    if name:
        return logger.bind(component=name)
    return logger
