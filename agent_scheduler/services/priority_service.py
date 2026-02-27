"""
优先级服务 - 智能排序和优先级管理
"""
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PriorityService:
    """优先级服务"""
    
    def __init__(self, demands_db=None):
        self._demands_db_ref = demands_db
    
    def _get_demands_db(self):
        if self._demands_db_ref is not None:
            return self._demands_db_ref
        from agent_scheduler.api.routes.demands import demands_db
        return demands_db
    
    def get_priority_stats(self) -> Dict[str, int]:
        demands_db = self._get_demands_db()
        stats = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        
        for demand in demands_db.values():
            priority = demand.get("priority", 2)
            key = f"P{priority}"
            if key in stats:
                stats[key] += 1
        
        return stats
    
    def sort_demands(self, demands: List[Dict], by: str = "priority") -> List[Dict]:
        if by == "priority":
            return sorted(demands, key=lambda d: (d.get("priority", 999), d.get("sort_order", 0)))
        elif by == "stage":
            stage_order = {"WATCHING": 0, "VALIDATING": 1, "BUILDING": 2, "SHIPPED": 3}
            return sorted(demands, key=lambda d: stage_order.get(d.get("stage", ""), 999))
        elif by == "created":
            return sorted(demands, key=lambda d: d.get("created_at", datetime.min))
        elif by == "updated":
            return sorted(demands, key=lambda d: d.get("updated_at", datetime.min), reverse=True)
        return demands
    
    def reorder(self, demand_id: str, new_order: int) -> Dict:
        demands_db = self._get_demands_db()
        
        if demand_id not in demands_db:
            return {"success": False, "error": "Demand not found"}
        
        demand = demands_db[demand_id]
        old_order = demand.get("sort_order", 0)
        
        if new_order < old_order:
            for d in demands_db.values():
                if old_order >= d.get("sort_order", 0) >= new_order:
                    d["sort_order"] = d.get("sort_order", 0) + 1
        else:
            for d in demands_db.values():
                if new_order <= d.get("sort_order", 0) <= old_order:
                    d["sort_order"] = d.get("sort_order", 0) - 1
        
        demand["sort_order"] = new_order
        demand["updated_at"] = datetime.now()
        
        return {"success": True, "old_order": old_order, "new_order": new_order}
    
    def suggest_priority(self, demand_id: str) -> Dict:
        demands_db = self._get_demands_db()
        
        if demand_id not in demands_db:
            return {"success": False, "error": "Demand not found"}
        
        demand = demands_db[demand_id]
        tags = demand.get("tags", [])
        category = demand.get("category", "")
        
        urgent_tags = ["紧急", "urgent", "hotfix", "critical"]
        if any(t.lower() in urgent_tags for t in tags):
            suggested = 0
        elif category == "Bug":
            suggested = 1
        else:
            suggested = 2
        
        factors = []
        if any(t.lower() in urgent_tags for t in tags):
            factors.append("含紧急标签")
        if category == "Bug":
            factors.append("Bug类型")
        
        return {"success": True, "suggested_priority": suggested, "suggested_label": f"P{suggested}", "factors": factors if factors else ["默认推荐"]}
    
    def get_priority_matrix(self) -> Dict[str, Dict]:
        demands_db = self._get_demands_db()
        matrix = {}
        
        for priority in range(4):
            p_key = f"P{priority}"
            matrix[p_key] = {}
            for stage in ["WATCHING", "VALIDATING", "BUILDING", "SHIPPED"]:
                count = sum(1 for d in demands_db.values() if d.get("priority") == priority and d.get("stage") == stage)
                matrix[p_key][stage] = count
        
        return matrix
    
    def auto_balance(self) -> Dict:
        demands_db = self._get_demands_db()
        total = len(demands_db)
        
        if total == 0:
            return {"success": True, "message": "No demands to balance"}
        
        suggestions = []
        target_ratios = {"WATCHING": 0.2, "VALIDATING": 0.3, "BUILDING": 0.4, "SHIPPED": 0.1}
        
        for stage, ratio in target_ratios.items():
            current = sum(1 for d in demands_db.values() if d.get("stage") == stage)
            target = int(total * ratio)
            diff = target - current
            
            if diff != 0:
                suggestions.append({
                    "stage": stage,
                    "current": current,
                    "target": target,
                    "recommendation": f"{'需要添加' if diff > 0 else '建议移出'}{abs(diff)}个需求"
                })
        
        return {"success": True, "total_demands": total, "suggestions": suggestions}
