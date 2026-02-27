"""
Workflow Engine API
"""
from .templates import router as templates_router, init_service as init_templates
from .executions import router as executions_router, init_service as init_executions

def init_all():
    init_templates()
    init_executions()

__all__ = ["templates_router", "executions_router", "init_all"]
