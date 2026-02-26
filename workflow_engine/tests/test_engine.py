"""
工作流引擎单元测试
"""
import unittest
from datetime import datetime

from workflow_engine.models.workflow import (
    WorkflowDefinition,
    WorkflowInstance,
    StepDefinition,
    StepStatus,
    WorkflowStatus,
    TaskDefinition,
    AgentSelector,
)
from workflow_engine.engine.state import InMemoryStateManager
from workflow_engine.engine.core import WorkflowEngine


class TestWorkflowModels(unittest.TestCase):
    """测试工作流模型"""
    
    def test_workflow_definition_creation(self):
        """测试工作流定义创建"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            version="1.0",
            description="Test description"
        )
        
        self.assertEqual(workflow.id, "test-workflow")
        self.assertEqual(workflow.name, "Test Workflow")
        self.assertEqual(workflow.version, "1.0")
        self.assertEqual(len(workflow.steps), 0)
    
    def test_workflow_get_step(self):
        """测试获取步骤"""
        step1 = StepDefinition(id="step1", name="Step 1")
        step2 = StepDefinition(id="step2", name="Step 2")
        
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            steps=[step1, step2]
        )
        
        self.assertEqual(workflow.get_step("step1"), step1)
        self.assertEqual(workflow.get_step("step2"), step2)
        self.assertIsNone(workflow.get_step("nonexistent"))
    
    def test_workflow_get_first_step(self):
        """测试获取第一个步骤"""
        step1 = StepDefinition(id="step1", name="Step 1")
        step2 = StepDefinition(id="step2", name="Step 2")
        
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            steps=[step1, step2]
        )
        
        self.assertEqual(workflow.get_first_step(), step1)
        
        # 空工作流
        empty_workflow = WorkflowDefinition(id="empty", name="Empty")
        self.assertIsNone(empty_workflow.get_first_step())
    
    def test_task_definition_with_agent_selector(self):
        """测试带Agent选择器的任务定义"""
        selector = AgentSelector(
            agent_type="dev-engineer",
            capabilities=["coding", "testing"]
        )
        
        task = TaskDefinition(
            id="task1",
            name="Test Task",
            executor_type="agent",
            agent_selector=selector
        )
        
        self.assertEqual(task.agent_selector.agent_type, "dev-engineer")
        self.assertIn("coding", task.agent_selector.capabilities)


class TestInMemoryStateManager(unittest.TestCase):
    """测试内存状态管理器"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = InMemoryStateManager()
    
    def test_save_and_load_workflow(self):
        """测试保存和加载工作流"""
        instance = WorkflowInstance(
            id="wf-001",
            definition_id="test-def",
            status=WorkflowStatus.PENDING
        )
        
        self.manager.save_workflow(instance)
        
        loaded = self.manager.load_workflow("wf-001")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, "wf-001")
        self.assertEqual(loaded.definition_id, "test-def")
    
    def test_list_workflows(self):
        """测试列出工作流"""
        # 保存多个工作流
        for i in range(3):
            instance = WorkflowInstance(
                id=f"wf-{i:03d}",
                definition_id="test-def",
                status=WorkflowStatus.PENDING
            )
            self.manager.save_workflow(instance)
        
        workflows = self.manager.list_workflows()
        self.assertEqual(len(workflows), 3)
    
    def test_delete_workflow(self):
        """测试删除工作流"""
        instance = WorkflowInstance(id="wf-001", definition_id="test-def")
        self.manager.save_workflow(instance)
        
        self.manager.delete_workflow("wf-001")
        loaded = self.manager.load_workflow("wf-001")
        self.assertIsNone(loaded)
    
    def test_clear(self):
        """测试清空状态"""
        instance = WorkflowInstance(id="wf-001", definition_id="test-def")
        self.manager.save_workflow(instance)
        
        self.manager.clear()
        workflows = self.manager.list_workflows()
        self.assertEqual(len(workflows), 0)


class TestWorkflowEngine(unittest.TestCase):
    """测试工作流引擎"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = WorkflowEngine()
        
        # 创建测试工作流
        self.workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            steps=[
                StepDefinition(
                    id="step1",
                    name="Step 1",
                    next_steps=["step2"]
                ),
                StepDefinition(
                    id="step2", 
                    name="Step 2",
                    next_steps=["step3"]
                ),
                StepDefinition(
                    id="step3",
                    name="Step 3",
                    next_steps=[]
                )
            ]
        )
    
    def test_engine_creation(self):
        """测试引擎创建"""
        self.assertIsNotNone(self.engine.state_manager)
        self.assertIn("agent", self.engine.task_executors)
    
    def test_execute_simple_workflow(self):
        """测试执行简单工作流"""
        instance = self.engine.execute(self.workflow)
        
        self.assertEqual(instance.status, WorkflowStatus.COMPLETED)
        self.assertEqual(len(instance.completed_steps), 3)
        self.assertEqual(instance.failed_steps, [])
    
    def test_execute_with_input_data(self):
        """测试带输入数据的执行"""
        input_data = {"key": "value", "number": 42}
        
        instance = self.engine.execute(self.workflow, input_data=input_data)
        
        self.assertEqual(instance.input_data, input_data)
    
    def test_get_status(self):
        """测试获取状态"""
        # 先执行
        instance = self.engine.execute(self.workflow)
        
        # 通过ID获取
        loaded = self.engine.get_status(instance.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, instance.id)
        self.assertEqual(loaded.status, WorkflowStatus.COMPLETED)
    
    def test_list_workflows(self):
        """测试列出工作流"""
        # 执行多个工作流
        for i in range(3):
            self.engine.execute(self.workflow)
        
        workflows = self.engine.list_workflows()
        self.assertGreaterEqual(len(workflows), 3)


class TestWorkflowWithTasks(unittest.TestCase):
    """测试带任务的工作流"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = WorkflowEngine()
        
        # 创建带任务的工作流
        task = TaskDefinition(
            id="task1",
            name="Test Task",
            executor_type="agent",
            agent_selector=AgentSelector(agent_type="dev-engineer")
        )
        
        self.workflow = WorkflowDefinition(
            id="task-workflow",
            name="Task Workflow",
            steps=[
                StepDefinition(
                    id="step1",
                    name="Step with Task",
                    task_def=task,
                    next_steps=[]
                )
            ]
        )
    
    def test_execute_with_task(self):
        """测试执行带任务的工作流"""
        instance = self.engine.execute(self.workflow)
        
        self.assertEqual(instance.status, WorkflowStatus.COMPLETED)


if __name__ == '__main__':
    unittest.main()
