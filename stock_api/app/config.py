# -*- coding: utf-8 -*-
"""
配置管理
"""
import os
import secrets

# JWT配置 - 必须从环境变量读取，不提供默认值
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("必须设置 JWT_SECRET_KEY 环境变量")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS", "24"))

# API配置
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8002"))

# CORS白名单 - 必须从环境变量读取，不允许所有来源
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else []
if not CORS_ORIGINS:
    raise ValueError("必须设置 CORS_ORIGINS 环境变量")
