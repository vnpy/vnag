# 0.1.0

## 历史会话的标签化存储
- 设置标题（实现位置：vnag/vnag/session_manager.py → save_session 自动生成标题）
- 会话删除（实现位置：vnag/vnag/session_manager.py → delete_session/restore_session/cleanup_deleted_sessions）
- 历史导出（实现位置：vnag/vnag/session_manager.py → export_session；UI 触发见 window.py）

## 轻量级向量化数据库支持
- 数据库选型（优先考虑Chroma）（实现位置：vnag/vnag/vector_service.py 使用 ChromaDB）
- 标准化导入和查询接口设计（实现位置：DocumentService.process_file + VectorService.add_documents/similarity_search）

## 提供文档内容导入工具
- 文档分段拆分（实现位置：vnag/vnag/document_service.py → _create_chunks_markdown 标题感知分块）
- Embedding模型选型（优先考虑BGE：BAAI General Embedding）（实现位置：vnag/vnag/vector_service.py 使用 BGE-large-zh-v1.5）
- 图形化导入UI（当前：MVP 采用 .vnag/docs 自动导入，未提供单独导入向导；后续阶段规划）

## 实现标准化RAG回答生成
- 相关资料检索（片段 vs 全文）（实现位置：VectorService.similarity_search 返回分块 Top-K；全文检索暂未实现）
- prompt模板设计开发（实现位置：vnag/vnag/template.py → CHAT_PROMPT_TEMPLATE/RAG_PROMPT_TEMPLATE）
- 对接OpenRounter发送请求（实现位置：vnag/vnag/gateway.py → invoke_streaming 使用 OpenAI 兼容接口）

## Markdown前端显示方案
- 基础渲染实现（问、答）（实现位置：vnag/vnag/window.py → append_message 使用 markdown 渲染回答）
- 代码渲染优化（实现位置：vnag/vnag/window.py → markdown 扩展 fenced_code/codehilite，基础高亮已启用）
- 回答全文复制（未实现，后续阶段）
- 特定内容复制（如代码）（未实现，后续阶段）
