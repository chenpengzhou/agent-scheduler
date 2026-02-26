# 当前任务

## 工作流引擎 - 迭代1（MVP基础框架）

**派发时间**：2026-02-25
**派发人**：CEO（愚者会长）
**状态**：待开始

---

### 目标
让第一个简单工作流能跑起来

### 核心需求
1. 核心数据模型 - Task/Workflow/State三个模型能正确定义和序列化
2. 内存状态管理 - 状态存储在内存中，支持CRUD操作
3. 顺序执行引擎 - 能按顺序执行多个步骤，无并行
4. 命令行工具 - 能通过CLI触发工作流执行
5. 错误处理 - 执行失败时能捕获异常并记录
6. 状态输出 - 执行过程中能输出状态变化

### 交付物
- `workflow_engine/` 目录（包含engine/, models/, cli/子目录）
- `engine/core.py` - 工作流引擎核心
- `engine/state.py` - 状态管理
- `models/workflow.py` - 数据模型
- `cli/main.py` - 命令行工具
- `examples/hello.yaml` - 示例工作流
- `tests/` - 单元测试（覆盖率>80%）

### 验收标准
- [ ] 能通过 `workflow-cli run examples/hello.yaml` 成功执行工作流
- [ ] 执行过程中能看到状态变化输出（PENDING → RUNNING → COMPLETED）
- [ ] 3个步骤按顺序执行，无并行
- [ ] 执行完成后能查看结果

### 工期
3-5天
