# 反馈收集服务

用于收集vnag用户的对话反馈，支持评价（赞/踩）和评论。

## 功能特性

- 收集完整对话内容（session）和配置信息（profile）
- 支持用户评价（thumbs_up/thumbs_down）和评论
- SQLite存储元数据，文件系统存储大文件
- Profile基于hash去重，避免重复存储
- 支持upsert，同一session多次上传会更新记录

## 安装依赖

```bash
pip install -e ".[feedback]"
```

## 启动服务器

```bash
# 默认端口8000
uvicorn feedback_server.app:app --reload --port 8000

# 自定义数据存储目录（可选）
export FEEDBACK_STORAGE_DIR=/path/to/data
uvicorn feedback_server.app:app --reload --port 8000
```

## 测试

运行测试脚本验证功能：

```bash
# 1. 先启动服务器
uvicorn feedback_server.app:app --reload --port 8000

# 2. 在另一个终端运行测试
python examples/feedback/run_feedback_test.py
```

测试内容包括：
- 基础上传（thumbs_up/thumbs_down）
- 查询反馈
- 批量加载
- UPSERT功能

## 数据存储结构

```
feedback_data/
├── feedback.db                    # SQLite数据库
├── test_user_001/
│   ├── sessions/
│   │   └── 2025/01/24/
│   │       └── {session_id}.json  # session内容
│   └── profiles/
│       └── {hash}--{name}.json    # profile配置（去重）
└── test_user_002/
    ├── sessions/
    └── profiles/
```

## API接口

### 1. 上传反馈

```
POST /api/feedback
```

参数（multipart/form-data）：
- `session_file`: 会话JSON文件
- `profile_file`: 配置JSON文件
- `user_id`: 用户ID
- `session_id`: 会话ID
- `session_name`: 会话名称
- `profile_name`: 配置名称
- `profile_hash`: 配置内容哈希
- `model`: 模型名称
- `rating`: 评价（thumbs_up/thumbs_down）
- `comment`: 评论（可选）

### 2. 加载反馈

```
GET /api/feedbacks?user_id={user_id}&rating={rating}&start_time={start}&end_time={end}
```

参数（可选）：
- `user_id`: 按用户过滤
- `rating`: 按评价过滤（thumbs_up/thumbs_down）
- `start_time`: 起始时间（ISO格式，如"2025-12-01"）
- `end_time`: 结束时间（ISO格式）

不传参数则返回所有反馈。

## 数据库查询

使用SQLite命令行查询：

```bash
sqlite3 feedback_data/feedback.db
```

常用查询：

```sql
-- 查看所有反馈
SELECT user_id, session_id, session_name, rating, messages_count, updated_at 
FROM DbFeedbackSession;

-- 查看表结构
.schema DbFeedbackSession

-- 查看踩的反馈
SELECT session_name, model, comment, updated_at 
FROM DbFeedbackSession 
WHERE rating = 'thumbs_down';

-- 按用户统计
SELECT user_id, COUNT(*) as count 
FROM DbFeedbackSession 
GROUP BY user_id;

-- 按模型统计
SELECT model, COUNT(*) as count, AVG(messages_count) as avg_messages
FROM DbFeedbackSession 
GROUP BY model;

-- 退出
.quit
```

## 技术架构

- **Web框架**: FastAPI
- **数据库**: SQLite + Peewee ORM
- **存储方式**: 混合存储（元数据在数据库，文件在文件系统）
- **去重策略**: Profile基于内容hash去重

## 开发计划

当前实现：
- [x] 后端服务（database + API）
- [x] 测试脚本

待实现（本地测试，暂不提交）：
- [ ] vnag客户端集成（engine状态管理）
- [ ] 上传模块（feedback.py）
- [ ] UI反馈弹窗
- [ ] 删除/退出自动上传

