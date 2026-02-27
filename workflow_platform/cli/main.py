"""
工作流引擎CLI
"""
import argparse
import sys
import yaml
import json
from pathlib import Path

from workflow_platform.models.workflow import WorkflowDefinition, StepDefinition, TaskDefinition, AgentSelector
from workflow_platform.engine.core import WorkflowEngine
from workflow_platform.engine.state import InMemoryStateManager


def load_workflow_from_file(file_path: str) -> WorkflowDefinition:
    """从文件加载工作流定义"""
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        if path.suffix in ['.yaml', '.yml']:
            data = yaml.safe_load(f)
        elif path.suffix == '.json':
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    # 解析工作流定义
    steps = []
    for step_data in data.get('steps', []):
        task_def = None
        if 'task' in step_data:
            task_data = step_data['task']
            agent_selector = None
            if 'agent_selector' in task_data:
                selector_data = task_data['agent_selector']
                agent_selector = AgentSelector(
                    agent_type=selector_data.get('agent_type', 'dev-engineer'),
                    capabilities=selector_data.get('capabilities', [])
                )
            task_def = TaskDefinition(
                id=task_data['id'],
                name=task_data['name'],
                description=task_data.get('description', ''),
                executor_type=task_data.get('executor_type', 'agent'),
                agent_selector=agent_selector,
                input_params=task_data.get('input_params', {})
            )
        
        step = StepDefinition(
            id=step_data['id'],
            name=step_data['name'],
            description=step_data.get('description', ''),
            task_def=task_def,
            next_steps=step_data.get('next_steps', [])
        )
        steps.append(step)
    
    workflow = WorkflowDefinition(
        id=data['id'],
        name=data['name'],
        version=data.get('version', '1.0'),
        description=data.get('description', ''),
        steps=steps,
        metadata=data.get('metadata', {})
    )
    
    return workflow


def cmd_run(args):
    """运行工作流"""
    print(f"📂 Loading workflow from: {args.file}")
    
    # 加载工作流定义
    workflow = load_workflow_from_file(args.file)
    
    print(f"✅ Loaded workflow: {workflow.name} (v{workflow.version})")
    print(f"   Steps: {len(workflow.steps)}")
    for i, step in enumerate(workflow.steps, 1):
        print(f"   {i}. {step.name} ({step.id})")
    print()
    
    # 解析输入参数
    input_data = {}
    if args.input:
        for item in args.input:
            if '=' in item:
                key, value = item.split('=', 1)
                input_data[key] = value
    
    # 创建引擎并执行
    engine = WorkflowEngine()
    
    print("=" * 50)
    instance = engine.execute(workflow, input_data=input_data)
    print("=" * 50)
    
    print(f"\n📊 Final Status: {instance.status.value}")
    print(f"   Workflow ID: {instance.id}")
    if instance.error_message:
        print(f"   Error: {instance.error_message}")
    
    return 0 if instance.status.value == 'COMPLETED' else 1


def cmd_status(args):
    """查看工作流状态"""
    engine = WorkflowEngine()
    
    if args.id:
        instance = engine.get_status(args.id)
        if not instance:
            print(f"❌ Workflow not found: {args.id}")
            return 1
        
        print(f"📋 Workflow Status")
        print(f"   ID: {instance.id}")
        print(f"   Definition ID: {instance.definition_id}")
        print(f"   Status: {instance.status.value}")
        print(f"   Created: {instance.created_at}")
        if instance.started_at:
            print(f"   Started: {instance.started_at}")
        if instance.completed_at:
            print(f"   Completed: {instance.completed_at}")
        print(f"   Completed Steps: {instance.completed_steps}")
        print(f"   Failed Steps: {instance.failed_steps}")
        if instance.error_message:
            print(f"   Error: {instance.error_message}")
    else:
        # 列出所有工作流
        workflows = engine.list_workflows()
        
        if not workflows:
            print("📭 No workflows found")
            return 0
        
        print(f"📋 Workflows ({len(workflows)}):")
        for wf in workflows:
            print(f"   {wf.id[:8]}... | {wf.status.value:10} | {wf.definition_id}")
    
    return 0


def cmd_list(args):
    """列出工作流"""
    return cmd_status(args)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='Workflow Engine CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # run 命令
    run_parser = subparsers.add_parser('run', help='Run a workflow')
    run_parser.add_argument('file', help='Workflow definition file (YAML or JSON)')
    run_parser.add_argument('-i', '--input', action='append', help='Input parameters (key=value)')
    run_parser.set_defaults(func=cmd_run)
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='Get workflow status')
    status_parser.add_argument('id', nargs='?', help='Workflow instance ID')
    status_parser.set_defaults(func=cmd_status)
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='List workflows')
    list_parser.set_defaults(func=cmd_list)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
