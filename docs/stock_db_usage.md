# 股票数据本地缓存系统使用说明

## 📁 文件结构

```
/home/robin/.openclaw/
├── data/
│   └── stock.db              # SQLite 数据库文件
└── workspace-dev/src/
    ├── init_db.py            # 数据库初始化脚本
    └── stock_db.py           # 数据管理模块
```

## 🗄️ 数据库结构

**表名**: `stock_daily`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| ts_code | TEXT | 股票代码，如 '000001.SZ' |
| trade_date | TEXT | 交易日期，格式 'YYYYMMDD' |
| open | REAL | 开盘价 |
| high | REAL | 最高价 |
| low | REAL | 最低价 |
| close | REAL | 收盘价 |
| volume | REAL | 成交量 |
| amount | REAL | 成交额 |
| update_time | TIMESTAMP | 更新时间 |

**索引**:
- 唯一索引: (ts_code, trade_date)
- 普通索引: trade_date

## 🚀 使用方法

### 1. 环境变量配置

```bash
# 设置 Tushare Token（建议写入 ~/.bashrc 或 ~/.zshrc）
export TUSHARE_TOKEN="your_token_here"
```

### 2. 基础使用

```python
from stock_db import (
    init_db,              # 初始化数据库
    get_stock_data,       # 获取单只股票数据
    save_stock_data,      # 保存单条数据
    save_stock_dataframe, # 批量保存 DataFrame
    get_daily_data,       # 获取当日所有股票
    delete_old_data,      # 清理旧数据
    get_cache_stats       # 查看缓存统计
)

# 初始化数据库（首次使用）
init_db()

# 获取单只股票数据（自动缓存）
data = get_stock_data('000001.SZ', '20250221')
print(data)
# 输出: {'ts_code': '000001.SZ', 'close': 11.23, ..., 'source': 'cache'|'api'}

# 获取当日全市场数据（自动缓存）
import pandas as pd
df = get_daily_data('20250221')
print(f"获取 {len(df)} 只股票数据")

# 查看缓存统计
stats = get_cache_stats()
print(f"缓存记录数: {stats['total_records']}")

# 清理90天前的旧数据
delete_old_data(days=90)
```

### 3. 与现有代码集成

修改 `/home/robin/github/stock-trading-system/src/push/stock_push_tushare.py`:

```python
# 在文件顶部添加
import sys
sys.path.insert(0, '/home/robin/.openclaw/workspace-dev/src')
from stock_db import get_daily_data, save_stock_dataframe

# 修改数据获取部分
# 原代码:
# df = pro.daily(trade_date=trade_date)

# 新代码（使用缓存）:
df = get_daily_data(trade_date)
if df.empty:
    df = pro.daily(trade_date=trade_date)
    save_stock_dataframe(df)
```

## 🔐 安全改进

### 原代码问题
1. **硬编码 TOKEN** - 敏感信息暴露在代码中
2. **无本地缓存** - 重复调用 API，浪费额度

### 解决方案
1. **使用环境变量** - 从 `os.environ` 读取 TOKEN
2. **本地 SQLite 缓存** - 减少 API 调用
3. **自动数据同步** - 先查本地，缺失自动从 API 获取并缓存

## 📊 缓存优势

| 指标 | 无缓存 | 有缓存 |
|------|--------|--------|
| API 调用次数 | 每次运行都调用 | 首次调用 |
| 数据获取速度 | 网络依赖 | 本地毫秒级 |
| 离线可用性 | 否 | 是 |
| Token 消耗 | 高 | 极低 |

## 🛠️ 维护命令

```bash
# 初始化数据库
python3 /home/robin/.openclaw/workspace-dev/src/init_db.py

# 查看数据库统计
python3 -c "from src.stock_db import get_cache_stats; print(get_cache_stats())"

# 手动清理旧数据
python3 -c "from src.stock_db import delete_old_data; delete_old_data(30)"
```

## ⚠️ 注意事项

1. **环境变量**: 首次使用需设置 `TUSHARE_TOKEN`
2. **磁盘空间**: 全量日数据约 10MB/天，注意定期清理
3. **数据时效**: 本地缓存数据，API 数据为准
