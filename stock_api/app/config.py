# -*- coding: utf-8 -*-
"""
配置管理
"""
import os

# JWT配置
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "stock-admin-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# API配置
API_HOST = "0.0.0.0"
API_PORT = 8002

# CORS白名单
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else ["*"]
