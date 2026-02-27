"""
需求流水线服务 - 阶段流转管理
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from ..models.demand import DemandStage

logger = logging.getLogger(__name__)

STAGE_TRANSITIONS = {
    DemandStage.WATCHING: [DemandStage.VALIDATING],
    DemandStage.VALIDATING: [DemandStage.BUILDING, DemandStage.WATCHING],
    DemandStage.BUILDING: [DemandStage.SHIPPED, DemandStage.VALIDATING],
    DemandStage.SHIPPED: [],
}


class PipelineService:
    """流水线服务"""
    
    def __init__(self, demands_db=None):
        self._demands_db_ref = demands_db
    
    def _get_demands_db(self):
        if self._demands_db_ref is not None:
            return self._demands_db_ref
        from agent_scheduler.api.routes.demands import demands_db
        return demands_db
    
    def can_transition(self, current_stage: str, target_stage: str) -> bool:
        """检查是否可以流转"""
        try:
            current = DemandStage(current_stage)
            target = DemandStage(target_stage)
        except ValueError:
            return False
        
        allowed = STAGE_TRANSITIONS.get(current, [])
        return target in allowed
    
    def transition(self, demand_id: str, target_stage: str, reason: str = "") -> Dict:
        """执行阶段流转"""
        demands_db = self._get_demands_db()
        
        if demand_id not in demands_db:
            return {"success": False, "error": "Demand not found"}
        
        demand = demands_db[demand_id]
        current_stage = demand.get("stage", "WATCHING")
        
        if not self.can_transition(current_stage, target_stage):
            return {"success": False, "error": f"Cannot transition from {current_stage} to {target_stage}"}
        
        old_stage = current_stage
        demand["stage"] = target_stage
        demand["updated_at"] = datetime.now()
        
        if "stage_history" not in demand:
            demand["stage_history"] = []
        
        demand["stage_history"].append({
            "from_stage": old_stage,
            "to_stage": target_stage,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Demand {demand_id} transitioned: {old_stage} -> {target_stage}")
        
        return {"success": True, "old_stage": old_stage, "new_stage": target_stage}
    
    def get_stage_stats(self) -> Dict[str, int]:
        """获取各阶段统计"""
        demands_db = self._get_demands_db()
        stats = {"WATCHING": 0, "VALIDATING": 0, "BUILDING": 0, "SHIPPED": 0}
        
        for demand in demands_db.values():
            stage = demand.get("stage", "WATCHING")
            if stage in stats:
                stats[stage] += 1
        
        return stats
    
    def get_demands_by_stage(self, stage: str) -> List[Dict]:
        """获取指定阶段的需求列表"""
        demands_db = self._get_demands_db()
        return [d for d in demands_db.values() if d.get("stage") == stage]
    
    def bulk_transition(self, demand_ids: List[str], target_stage: str) -> Dict:
        """批量流转"""
        demands_db = self._get_demands_db()
        results = []
        for demand_id in demand_ids:
            result = self.transition(demand_id, target_stage)
            results.append({"demand_id": demand_id, **result})
        
        success_count = sum(1 for r in results if r.get("success"))
        return {"total": len(demand_ids), "success": success_count, "failed": len(demand_ids) - success_count, "results": results}
    
    def get_stage_trend(self, days: int = 7) -> Dict:
        return self.get_stage_stats()
    
    def get_stage_average_time(self) -> Dict[str, float]:
        return {"WATCHING": 0.0, "VALIDATING": 0.0, "BUILDING": 0.0, "SHIPPED": 0.0}
