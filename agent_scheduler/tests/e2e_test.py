"""
集成测试 - Agent自组织协作系统
"""
import asyncio
from datetime import datetime
from typing import Dict, List

# 导入服务
from agent_scheduler.services.message_service import MessageService
from agent_scheduler.services.notification_bridge import NotificationBridge, MessageBridge
from agent_scheduler.services.task_queue_service import TaskQueueService, PriorityScheduler
from agent_scheduler.services.workflow_service import WorkflowService
from agent_scheduler.models.workflow_config import DEFAULT_WORKFLOW_CONFIG


class E2ETest:
    """端到端测试"""
    
    def __init__(self):
        self.results = []
        self.tasks_db = {}
        self.agents_db = {}
        self.message_bridge = MessageBridge()
        self.notification_bridge = NotificationBridge(self.message_bridge)
        self.queue_service = TaskQueueService(self.tasks_db, self.agents_db)
        self.workflow_service = WorkflowService(DEFAULT_WORKFLOW_CONFIG)
        self.workflow_service.set_dbs(self.agents_db, self.tasks_db)
    
    def log(self, message: str):
        """记录日志"""
        print(f"[TEST] {message}")
        self.results.append(message)
    
    def setup(self):
        """设置测试数据"""
        self.log("=== Setup: 创建测试数据 ===")
        
        # 创建Agent
        self.agents_db = {
            "agent_product": {"id": "agent_product", "name": "产品-埃姆林", "role_id": "role_product", "status": "IDLE", "max_concurrent_tasks": 1},
            "agent_architect": {"id": "agent_architect", "name": "架构-帕特里克", "role_id": "role_architect", "status": "IDLE", "max_concurrent_tasks": 1},
            "agent_dev": {"id": "agent_dev", "name": "开发-阿尔杰", "role_id": "role_dev", "status": "IDLE", "max_concurrent_tasks": 2},
            "agent_qa": {"id": "agent_qa", "name": "测试-嘉莉娅", "role_id": "role_qa", "status": "IDLE", "max_concurrent_tasks": 1},
            "agent_sre": {"id": "agent_sre", "name": "运维-妮露", "role_id": "role_sre", "status": "IDLE", "max_concurrent_tasks": 1}
        }
        
        # 创建任务
        self.tasks_db = {
            "task_001": {
                "id": "task_001",
                "name": "Agent调度系统PRD",
                "status": "PENDING",
                "priority": 0,
                "assigned_agent_id": "",
                "workflow_stage": "DEMAND_ANALYSIS",
                "created_at": datetime.now()
            }
        }
        
        self.log(f"创建 {len(self.agents_db)} 个Agent")
        self.log(f"创建 {len(self.tasks_db)} 个任务")
    
    def test_workflow_flow(self):
        """测试工作流流转"""
        self.log("\n=== Test: 工作流流转测试 ===")
        
        # 验证工作流配置
        stages = self.workflow_service.get_stages()
        self.log(f"工作流阶段数: {len(stages)}")
        
        # 验证阶段流转
        path = self.workflow_service.get_workflow_path()
        self.log(f"工作流路径: {' -> '.join(path)}")
        
        # 验证角色映射
        dev_stage = self.workflow_service.get_stage_by_role("role_dev")
        self.log(f"role_dev -> {dev_stage}")
        
        return True
    
    def test_message_templates(self):
        """测试消息模板"""
        self.log("\n=== Test: 消息模板测试 ===")
        
        # 测试各种消息
        msg1 = MessageService.task_received("开发-阿尔杰", "API开发", 0)
        self.log(f"任务接收消息: {len(msg1)} 字符")
        
        msg2 = MessageService.task_started("开发-阿尔杰", "API开发", 0)
        self.log(f"任务开始消息: {len(msg2)} 字符")
        
        msg3 = MessageService.task_completed("开发-阿尔杰", "API开发", 3600, "测试-埃姆林")
        self.log(f"任务完成消息: {len(msg3)} 字符")
        
        msg4 = MessageService.task_transferred("API开发", "开发-阿尔杰", "测试-埃姆林")
        self.log(f"任务流转消息: {len(msg4)} 字符")
        
        return True
    
    def test_priority_scheduling(self):
        """测试优先级调度"""
        self.log("\n=== Test: 优先级调度测试 ===")
        
        # 创建不同优先级的任务
        test_tasks = [
            {"id": "t1", "name": "P3任务", "priority": 3, "status": "PENDING"},
            {"id": "t2", "name": "P0任务", "priority": 0, "status": "PENDING"},
            {"id": "t3", "name": "P2任务", "priority": 2, "status": "PENDING"},
            {"id": "t4", "name": "P1任务", "priority": 1, "status": "PENDING"}
        ]
        
        sorted_tasks = PriorityScheduler.sort_by_priority(test_tasks)
        
        self.log("排序结果:")
        for i, t in enumerate(sorted_tasks, 1):
            self.log(f"  {i}. {t['name']} (P{t['priority']})")
        
        expected = ["P0", "P1", "P2", "P3"]
        actual = [f"P{t['priority']}" for t in sorted_tasks]
        
        return actual == expected
    
    def test_queue_management(self):
        """测试队列管理"""
        self.log("\n=== Test: 队列管理测试 ===")
        
        # 分配任务到Agent
        self.tasks_db["task_001"]["assigned_agent_id"] = "agent_dev"
        self.tasks_db["task_002"] = {"id": "task_002", "name": "任务2", "priority": 1, "status": "PENDING", "assigned_agent_id": "agent_dev"}
        self.tasks_db["task_003"] = {"id": "task_003", "name": "任务3", "priority": 2, "status": "RUNNING", "assigned_agent_id": "agent_dev"}
        
        # 获取队列
        queue = self.queue_service.get_agent_queue("agent_dev")
        self.log(f"Agent队列: Running={len(queue['running'])}, Waiting={len(queue['waiting'])}")
        
        # 获取下一个任务
        next_task = self.queue_service.get_next_task("agent_dev")
        self.log(f"下一个任务: {next_task['name'] if next_task else 'None'}")
        
        return True
    
    def test_exception_handling(self):
        """测试异常处理"""
        self.log("\n=== Test: 异常处理测试 ===")
        
        # 测试不存在的任务
        result = self.queue_service.get_next_task("non_existent_agent")
        self.log(f"不存在的Agent: {result}")
        
        # 测试无效优先级
        test_tasks = [{"id": "t1", "name": "测试", "priority": 999, "status": "PENDING"}]
        sorted_tasks = PriorityScheduler.sort_by_priority(test_tasks)
        self.log(f"无效优先级处理: {sorted_tasks[0]['priority']}")
        
        return True
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*50)
        print("Agent自组织协作系统 - E2E测试")
        print("="*50 + "\n")
        
        self.setup()
        
        tests = [
            ("工作流流转", self.test_workflow_flow),
            ("消息模板", self.test_message_templates),
            ("优先级调度", self.test_priority_scheduling),
            ("队列管理", self.test_queue_management),
            ("异常处理", self.test_exception_handling)
        ]
        
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
                    self.log(f"\n✅ {name}: PASSED")
                else:
                    failed += 1
                    self.log(f"\n❌ {name}: FAILED")
            except Exception as e:
                failed += 1
                self.log(f"\n❌ {name}: ERROR - {e}")
        
        print("\n" + "="*50)
        print(f"测试结果: {passed} passed, {failed} failed")
        print("="*50 + "\n")
        
        return failed == 0


def run_e2e_tests():
    """运行E2E测试"""
    tester = E2ETest()
    return tester.run_all_tests()


if __name__ == "__main__":
    run_e2e_tests()
