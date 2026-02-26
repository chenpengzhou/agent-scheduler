# Workflow Engine

工作流引擎 - 让工作流能跑起来

## 安装

```bash
cd workflow_engine
pip install -e .
```

## 使用

### 运行工作流

```bash
python -m workflow_engine.cli.main run examples/hello.yaml
```

### 查看状态

```bash
# 列出所有工作流
python -m workflow_engine.cli.main list

# 查看指定工作流状态
python -m workflow_engine.cli.main status <workflow_id>
```

## 项目结构

```
workflow_engine/
├── engine/          # 核心引擎
│   ├── core.py      # 工作流引擎
│   └── state.py     # 状态管理
├── models/          # 数据模型
│   └── workflow.py  # 工作流模型
├── cli/             # 命令行工具
│   └── main.py      # CLI入口
├── examples/        # 示例
│   └── hello.yaml   # Hello World示例
└── tests/           # 单元测试
    └── test_engine.py
```

## 验收标准

- [x] 能通过CLI成功执行工作流
- [x] 执行过程中能看到状态变化输出（PENDING → RUNNING → COMPLETED）
- [x] 3个步骤按顺序执行，无并行
- [x] 执行完成后能查看结果
- [x] 单元测试通过
