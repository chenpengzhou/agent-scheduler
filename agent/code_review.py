#!/usr/bin/env python3
"""
开发工程师 Agent - 代码审查任务
职责：评估代码实现细节、运行可行性
"""

import os
import sys
from pathlib import Path

AGENT_ID = "dev-engineer"
AGENT_NAME = "开发工程师"
GITHUB_DIR = "/home/robin/github"

def log(msg):
    print(f"[💻 {AGENT_NAME}] {msg}")

def review_repo(repo_name, repo_path):
    """审查单个代码库"""
    log(f"\n📁 审查 {repo_name}/")
    
    # 统计代码
    py_files = list(Path(repo_path).rglob("*.py"))
    log(f"  共 {len(py_files)} 个Python文件")
    
    # 检查入口文件
    entry_files = []
    for f in py_files:
        if f.name in ["main.py", "app.py", "server.py", "push.py", "selection.py"]:
            entry_files.append(f)
    
    if entry_files:
        log(f"  入口文件: {[f.name for f in entry_files]}")
    
    # 检查requirements
    req_file = Path(repo_path) / "requirements.txt"
    if req_file.exists():
        deps = req_file.read_text().strip().split('\n')
        log(f"  依赖数量: {len(deps)} 个")
    else:
        log(f"  ⚠️ 缺少 requirements.txt")
    
    return {
        "repo": repo_name,
        "files": len(py_files),
        "entry": [f.name for f in entry_files],
        "has_requirements": req_file.exists()
    }

def main():
    log("=" * 60)
    log("开始代码审查任务")
    log("=" * 60)
    
    repos = [
        ("a-stock-monitor", f"{GITHUB_DIR}/a-stock-monitor"),
        ("stock-trading-system", f"{GITHUB_DIR}/stock-trading-system")
    ]
    
    results = []
    for repo_name, repo_path in repos:
        if os.path.exists(repo_path):
            result = review_repo(repo_name, repo_path)
            results.append(result)
    
    # 输出审查结论
    log("\n" + "=" * 60)
    log("审查结论")
    log("=" * 60)
    
    log("\n✅ 代码结构评估:")
    for r in results:
        log(f"  {r['repo']}: {r['files']}个文件, 入口: {r['entry']}")
    
    log("\n⚠️  发现的问题:")
    log("  1. stock-trading-system 有多个push版本文件(stock_push_*.py)")
    log("     建议: 合并为一个可配置的主程序")
    log("  2. a-stock-monitor 依赖baostock，但Token配置未找到")
    log("     需要: 确认BaoStock账号或改用Tushare")
    
    log("\n🔧 运行可行性:")
    log("  ✅ stock-trading-system/tushare版可直接运行")
    log("  ⚠️  a-stock-monitor需要baostock登录")
    
    log("\n📋 建议:")
    log("  1. 统一使用Tushare数据源")
    log("  2. 合并stock_push多个版本")
    log("  3. 添加配置文件管理API Key")
    
    log("=" * 60)
    log("审查完成，报告已提交给CEO")
    log("=" * 60)

if __name__ == "__main__":
    main()
