"""
优先级服务 - 智能排序和优先级管理
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from ..models.demand import Demand, DemandPriority, DemandStage

logger = logging.getLogger(__name__)


class PriorityService:
    """优先级服务"""
    
    def __init__(self, demands_db: Dict[str, Dict] = None):
        self.demands_db = demands_db or {}
    
    def get_priority_stats(self) -> Dict[str, int]:
        """获取各优先级统计"""
        stats = {
            "P0": 0,
            "P1": 0,
            "P2": 0,
            "P3": 0
        }
        
        for demand in self.demands_db.values():
            priority = demand.get("priority", 2)
            key = f"P{priority}"
            if key in stats:
                stats[key] += 1
        
        return stats
    
    def sort_demands(self, demands: List[Dict], by: str = "priority") -> List[Dict]:
        """排序需求"""
        if by == "priority":
            # 按优先级排序（P0在前）
            return sorted(demands, key=lambda d: (
                d.get("priority", 999),
                d.get("sort_order", 0)
            ))
        elif by == "stage":
            # 按阶段排序
            stage_order = {
                "WATCHING": 0,
                "VALIDATING": 1,
                "BUILDING": 2,
                "SHIPPED": 3
            }
            return sorted(demands, key=lambda d: stage_order.get(d.get("stage", ""), 999))
        elif by == "created":
            # 按创建时间排序
            return sorted(demands, key=lambda d: d.get("created_at", datetime.min))
        elif by == "updated":
            # 按更新时间排序
            return sorted(demands, key=lambda d: d.get("updated_at", datetime.min), reverse=True)
        
        return demands
    
    def reorder(self, demand_id: str, new_order: int) -> Dict:
        """调整需求顺序"""
        if demand_id not in self.demands_db:
            return {"success": False, "error": "Demand not found"}
        
        demand = self.demands_db[demand_id]
        old_order = demand.get("sort_order", 0)
        
        # 更新排序
        if new_order < old_order:
            # 向前移动：后面的需求顺序+1
            for d in self.demands_db.values():
                if old_order >= d.get("sort_order", 0) >= new_order:
                    d["sort_order"] = d.get("sort_order", 0) + 1
        else:
            # 向后移动：前面的需求顺序-1
            for d in self.demands_db.values():
                if new_order <= d.get("sort_order", 0) <= old_order:
                    d["sort_order"] = d.get("sort_order", 0) - 1
        
        demand["sort_order"] = new_order
        demand["updated_at"] = datetime.now()
        
        return {"success": True, "old_order": old_order, "new_order": new_order}
    
    def suggest_priority(self, demand_id: str) -> Dict:
        """智能推荐优先级（基于价值/紧急度）"""
        if demand_id not in self.demands_db:
            return {"success": False, "error": "Demand not found"}
        
        demand = self.demands_db[demand_id]
        
        # 简化算法：根据标签和类型推断
        tags = demand.get("tags", [])
        category = demand.get("category", "")
        
        # 紧急标签
        urgent_tags = ["紧急", "urgent", "hotfix", "critical"]
        if any(t.lower() in urgent_tags for t in tags):
            suggested = 0  # P0
        elif category == "Bug":
            suggested = 1  # P1
        else:
            suggested = 2  # P2
        
        factors = []
        if any(t.lower() in urgent_tags for t in tags):
            factors.append("含紧急标签")
        if category == "Bug":
            factors.append("Bug类型")
        
        return {
            "success": True,
            "suggested_priority": suggested,
            "suggested_label": f"P{suggested}",
            "factors": factors if factors else ["默认推荐"]
        }
    
    def get_priority_matrix(self) -> Dict[str, Dict]:
        """获取优先级矩阵（优先级 x 阶段）"""
        matrix = {}
        
        for priority in range(4):
            p_key = f"P{priority}"
            matrix[p_key] = {}
            for stage in ["WATCHING", "VALIDATING", "BUILDING", "SHIPPED"]:
                count = sum(
                    1 for d in self.demands_db.values()
                    if d.get("priority") == priority and d.get("stage") == stage
                )
                matrix[p_key][stage] = count
        
        return matrix
    
    def auto_balance(self) -> Dict:
        """自动平衡各阶段需求数量"""
        stage_stats = {
            "WATCHING": [],
            "VALIDATING": [],
            "BUILDING": [],
            "SHIPPED": []
        }
        
        # 按优先级分组
        for demand in self.demands_db.values():
            stage = demand.get("stage", "WATCHING")
            if stage in stage_stats:
                stage_stats[stage].append(demand)
        
        # 理想比例：WATCHING 20%, VALIDATING 30%, BUILDING 40%, SHIPPED 10%
        total = len(self.demands_db)
        if total == 0:
            return {"success": True, "message": "No demands to balance"}
        
        suggestions = []
        target_ratios = {"WATCHING": 0.2, "VALIDATING": 0.3, "BUILDING": 0.4, "SHIPPED": 0.1}
        
        for stage, ratio in target_ratios.items():
            current = len(stage_stats[stage])
            target = int(total * ratio)
            diff = target - current
            
            if diff > 0:
                suggestions.append({
                    "stage": stage,
                    "current": current,
                    "target": target,
                    "recommendation": f"需要添加{diff}个需求到{stage}阶段"
                })
            elif diff < 0:
                suggestions.append({
                    "stage": stage,
                    "current": current,
                    "target": target,
                    "recommendation": f"建议移出{abs(diff)}个需求从{stage}阶段"
                })
        
        return {
            "success": True,
            "total_demands": total,
            "suggestions": suggestions
        }
