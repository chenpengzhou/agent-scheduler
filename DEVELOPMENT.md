# 开发规范

## Git Workflow
1. 从main创建feature分支: `git checkout -b feature/xxx`
2. 开发完成后提交PR
3. 架构师代码审查
4. 合并到main

## 代码规范
- 函数必须有docstring
- 关键逻辑加注释
- 单元测试覆盖率>80%

## 提交信息格式
```
feat: 新功能
fix: 修复bug
docs: 文档更新
refactor: 重构
test: 测试相关
```
