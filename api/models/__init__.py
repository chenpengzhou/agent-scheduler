"""
数据库初始化模块
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .db import Base


class Database:
    """数据库管理类"""
    
    def __init__(self, database_url: str = "sqlite:///./workflow_engine.db", echo: bool = False):
        self.engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_all(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_all(self):
        """删除所有表"""
        Base.metadata.drop_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# 全局数据库实例
_db: Database = None


def init_db(database_url: str = "sqlite:///./workflow_engine.db", echo: bool = False) -> Database:
    """初始化数据库"""
    global _db
    _db = Database(database_url, echo)
    _db.create_all()
    return _db


def get_db():
    """获取数据库会话 - FastAPI依赖"""
    global _db
    if _db is None:
        _db = init_db()
    
    session = _db.SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
