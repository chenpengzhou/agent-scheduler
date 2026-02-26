"""
条件模型 - 支持条件分支
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable
import re
import json


@dataclass
class Condition:
    """条件定义"""
    expression: str  # 例如: ${variable == "value"}
    target_step_id: str  # 满足条件时跳转的步骤
    otherwise_step_id: Optional[str] = None  # 不满足条件时跳转的步骤


@dataclass
class StepDependsOn:
    """步骤依赖"""
    step_ids: list = field(default_factory=list)  # 依赖的步骤ID列表
    strategy: str = "all"  # "all" - 全部完成, "any" - 任一完成


class ConditionEvaluator:
    """条件表达式求值器"""
    
    # 支持的操作符
    OPERATORS = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: float(a) > float(b),
        "<": lambda a, b: float(a) < float(b),
        ">=": lambda a, b: float(a) >= float(b),
        "<=": lambda a, b: float(a) <= float(b),
        "in": lambda a, b: a in b,
        "not in": lambda a, b: a not in b,
    }
    
    @classmethod
    def evaluate(cls, expression: str, context: Dict[str, Any]) -> bool:
        """求值条件表达式"""
        # 提取变量和操作符
        # 格式: ${variable operator value}
        # 例如: ${status == "completed"} 或 ${count > 5}
        
        pattern = r'\$\{([^}]+)\}'
        match = re.search(pattern, expression)
        
        if not match:
            return True
        
        expr_content = match.group(1).strip()
        
        # 解析表达式
        for op, func in cls.OPERATORS.items():
            if op in expr_content:
                parts = expr_content.split(op)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    var_value = parts[1].strip()
                    
                    # 获取上下文中的变量值
                    actual_value = cls._get_value(var_name, context)
                    
                    # 解析期望值
                    expected_value = cls._parse_value(var_value)
                    
                    return func(actual_value, expected_value)
        
        # 默认返回True
        return True
    
    @classmethod
    def _get_value(cls, var_name: str, context: Dict[str, Any]) -> Any:
        """获取上下文中的变量值"""
        # 支持嵌套访问，如: step1.output.result
        parts = var_name.split(".")
        
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    @classmethod
    def _parse_value(cls, value_str: str) -> Any:
        """解析值字符串"""
        value_str = value_str.strip()
        
        # 字符串
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]
        
        # 布尔值
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False
        
        # JSON数组/对象
        if value_str.startswith("[") or value_str.startswith("{"):
            try:
                return json.loads(value_str)
            except:
                pass
        
        # 数字
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except:
            pass
        
        # 字符串（未匹配到其他类型）
        return value_str


class ExecutionStrategy:
    """执行策略"""
    
    SEQUENTIAL = "sequential"  # 串行
    PARALLEL = "parallel"     # 并行
    MIXED = "mixed"           # 混合
    
    @classmethod
    def determine_ready_steps(
        cls,
        completed_steps: list,
        pending_steps: list,
        depends_on_map: Dict[str, StepDependsOn]
    ) -> list:
        """确定哪些步骤可以执行"""
        ready = []
        
        for step in pending_steps:
            deps = depends_on_map.get(step.id)
            
            if not deps:
                # 无依赖，任何时候都可执行
                ready.append(step)
                continue
            
            if deps.strategy == "all":
                # 全部依赖完成
                if all(dep_id in completed_steps for dep_id in deps.step_ids):
                    ready.append(step)
            elif deps.strategy == "any":
                # 任一依赖完成
                if any(dep_id in completed_steps for dep_id in deps.step_ids):
                    ready.append(step)
        
        return ready
