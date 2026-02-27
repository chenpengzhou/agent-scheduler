"""
工作流引擎 - 集成测试
测试所有迭代功能的集成
"""
import sys
sys.path.insert(0, '.')

from workflow_platform import (
    WorkflowEngine, ParallelExecutor, DAGExecutor, DAGBuilder,
    WorkflowDefinition, WorkflowInstance, StepDefinition, TaskDefinition,
    StepType, ApprovalService, NotificationService
)
from workflow_platform.models.workflow import WorkflowStatus, StepStatus


def test_iteration1_simple_workflow():
    """迭代1：简单顺序工作流"""
    print("\n=== 测试：迭代1 - 简单顺序工作流 ===")
    
    steps = [
        StepDefinition(
            id='step1', name='步骤1',
            task_def=TaskDefinition(id='t1', name='任务1', executor_type='script')
        ),
        StepDefinition(
            id='step2', name='步骤2',
            task_def=TaskDefinition(id='t2', name='任务2', executor_type='script')
        ),
        StepDefinition(
            id='step3', name='步骤3',
            task_def=TaskDefinition(id='t3', name='任务3', executor_type='script')
        ),
    ]
    
    wf_def = WorkflowDefinition(id='test1', name='简单工作流', steps=steps)
    engine = WorkflowEngine()
    result = engine.execute(wf_def, input_data={'test': 'data'})
    
    assert result.status == WorkflowStatus.COMPLETED, f"预期COMPLETED，实际{result.status}"
    print(f"✅ 状态: {result.status.value}")
    return True


def test_iteration2_persistence():
    """迭代2：持久化"""
    print("\n=== 测试：迭代2 - SQLite持久化 ===")
    
    from api.models import init_db, get_db
    from api.services.workflow_svc import WorkflowService
    
    # 初始化数据库
    db = init_db("sqlite:///./test_workflow.db", echo=False)
    
    # 使用session
    for session in get_db():
        svc = WorkflowService(session)
        
        # 创建定义
        definition = svc.create_definition(
            name="持久化测试",
            definition_json={'steps': [{'id': 's1', 'name': '测试'}]}
        )
        assert definition.id is not None
        print(f"✅ 定义创建: {definition.id}")
        
        # 启动实例
        instance = svc.start_instance(definition.id, {'test': 'data'})
        assert instance.id is not None
        print(f"✅ 实例创建: {instance.id}")
        
        # 查询实例
        loaded = svc.get_instance(instance.id)
        assert loaded.id == instance.id
        print(f"✅ 实例加载: {loaded.id}")
    
    import os
    os.remove("./test_workflow.db")
    return True


def test_iteration3_dag_parallel():
    """迭代3：DAG并行"""
    print("\n=== 测试：迭代3 - DAG并行执行 ===")
    
    steps = [
        StepDefinition(id='s1', name='开始', task_def=TaskDefinition(id='t1', name='init', executor_type='script')),
        StepDefinition(id='s2', name='并行A', task_def=TaskDefinition(id='t2', name='taskA', executor_type='script')),
        StepDefinition(id='s3', name='并行B', task_def=TaskDefinition(id='t3', name='taskB', executor_type='script')),
        StepDefinition(id='s4', name='汇总', task_def=TaskDefinition(id='t4', name='final', executor_type='script')),
    ]
    
    wf_def = WorkflowDefinition(id='dag-test', name='DAG测试', steps=steps)
    depends_on = {'s2': ['s1'], 's3': ['s1'], 's4': ['s2', 's3']}
    
    executor = ParallelExecutor()
    result = executor.execute(wf_def, depends_on_map=depends_on)
    
    assert result.status == WorkflowStatus.COMPLETED
    print(f"✅ DAG执行: {result.status.value}")
    return True


def test_iteration4_approval():
    """迭代4：审批"""
    print("\n=== 测试：迭代4 - 审批流程 ===")
    
    notification_svc = NotificationService()
    approval_svc = ApprovalService(notification_svc)
    
    # 创建审批
    approval = approval_svc.create_approval(
        step_instance_id='step_approval',
        workflow_instance_id='wf_test',
        title='测试审批',
        content={'data': 'test'},
        approver='tester'
    )
    assert approval.status.value == 'PENDING'
    print(f"✅ 审批创建: {approval.status.value}")
    
    # 审批通过
    approval_svc.approve(approval.id, approved_by='tester', comment='通过')
    assert approval.status.value == 'APPROVED'
    print(f"✅ 审批通过: {approval.status.value}")
    
    # 审批拒绝
    approval2 = approval_svc.create_approval(
        step_instance_id='step_approval2',
        workflow_instance_id='wf_test2',
        title='测试审批2',
        approver='tester'
    )
    approval_svc.reject(approval2.id, rejected_by='tester', comment='拒绝')
    assert approval2.status.value == 'REJECTED'
    print(f"✅ 审批拒绝: {approval2.status.value}")
    
    return True


def test_iteration5_full_integration():
    """迭代5：完整集成"""
    print("\n=== 测试：迭代5 - 完整集成 ===")
    
    # 模拟完整工作流：顺序 -> 并行 -> 审批 -> 完成
    steps = [
        StepDefinition(id='s1', name='提交', task_def=TaskDefinition(id='t1', name='提交', executor_type='script')),
        StepDefinition(id='s2', name='并行A', task_def=TaskDefinition(id='t2', name='并行A', executor_type='script')),
        StepDefinition(id='s3', name='并行B', task_def=TaskDefinition(id='t3', name='并行B', executor_type='script')),
        StepDefinition(id='s4', name='审批', step_type='approval'),
        StepDefinition(id='s5', name='完成', task_def=TaskDefinition(id='t5', name='完成', executor_type='script')),
    ]
    
    wf_def = WorkflowDefinition(id='full-test', name='完整集成测试', steps=steps)
    depends_on = {'s2': ['s1'], 's3': ['s1'], 's4': ['s2', 's3'], 's5': ['s4']}
    
    executor = ParallelExecutor()
    result = executor.execute(wf_def, depends_on_map=depends_on)
    
    print(f"✅ 完整流程执行: {result.status.value}")
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("工作流引擎 - 全量集成测试")
    print("=" * 60)
    
    tests = [
        ("迭代1：简单工作流", test_iteration1_simple_workflow),
        ("迭代2：持久化", test_iteration2_persistence),
        ("迭代3：DAG并行", test_iteration3_dag_parallel),
        ("迭代4：审批", test_iteration4_approval),
        ("迭代5：完整集成", test_iteration5_full_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {name} - 通过")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name} - 失败: {e}")
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
