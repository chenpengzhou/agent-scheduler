# -*- coding: utf-8 -*-
"""
存储模块
"""
from .base import DataStorage
from .sqlite_storage import SQLiteStorage

__all__ = ['DataStorage', 'SQLiteStorage']
