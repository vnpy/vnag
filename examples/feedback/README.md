# 反馈收集服务示例

演示如何使用feedback_server收集用户反馈。

## 功能说明

反馈收集服务用于收集vnag用户的对话反馈，包括：
- 完整对话内容（session）
- 配置信息（profile）
- 用户评价（thumbs_up/thumbs_down）
- 评论内容

## 安装依赖

```bash
pip install -e ".[feedback]"
```

## 运行示例

### 1. 启动服务器

```bash
uvicorn feedback_server.app:app --reload --port 8000
```

### 2. 运行测试脚本

在另一个终端：

```bash
python examples/feedback/run_feedback_test.py
```

## 测试内容

- 上传反馈（thumbs_up/thumbs_down）
- 查询反馈
- 批量加载反馈
- 时间范围过滤
- UPSERT功能测试

## 查看数据

```bash
sqlite3 feedback_data/feedback.db
SELECT * FROM DbFeedbackSession;
.quit
```

