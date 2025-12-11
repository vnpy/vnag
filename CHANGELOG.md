# 0.4.0

## Add

1. 增加托盘栏小图标
2. HistoryWidget自动显示当前智能体欢迎语
3. input_widget关闭富文本支持

## Mod

1. 实现HistoryWidget缩放系数自动存储
2. 自动切换运行目录到.vnag所在路径
3. 优化CppSegmenter分段器，过滤include文件内容

# 0.3.0

## Add

1. AgentEngine添加工具注册函数
2. 添加openai_embedder子模块
3. 添加AgentTool，实现Multi-Agent支持

## Mod

1. 避免loguru日志记录和其他库冲突
2. 添加参数用于控制会话持久化

## Fix

1. 修复logger初始化问题
2. 修复仅有一个MCP服务时，服务名前缀的缺失问题

# 0.2.0

## Add

1. 添加智能体配置数据结构
2. 添加TaskAgent并调整AgentEngine完成适配
3. 添加执行细节日志跟踪器
4. 添加Python代码执行工具
5. 添加Web访问相关工具
6. 丰富本地文件工具
7. 添加嵌入模型开发模板embedder类
8. 添加Qdrant向量化数据库支持
9. 添加SessionWidget并重构聊天窗口

## Mod

1. 日志记录器调整为跟踪TaskAgent
2. 调整本地工具命名和MCP一致
3. 修改UI界面支持TaskAgent交互
4. 增加模型信息查询对话框
5. 优化功能对话框控件细节
6. 实现会话的删除和重发
7. 实现Enter发送，Shift+Enter换行
8. 实现自动生成会话名称
9. 更新项目示例examples

# 0.1.0

## Add

1. 添加基础框架
2. 重构BaseGateway，并实现OpenaiGateway
3. 实现AnthropicGateway
4. 阿里云DashscopeGateway（目前不支持工具调用）
5. 添加list_models函数用于查询所有支持的模型名称
6. 流式调用stream接口支持
7. 本地工具调用功能
8. MCP工具调用功能
9. 新增文件系统本地工具集
10. 新增网络本地工具集
11. 新增Agent引擎，并调整OpenaiGateway支持工具调用
12. 增加UI组件的AgentEngine工具调用支持
13. 重构UI相关组件功能
14. 添加基于HTML渲染Markdown返回内容
15. 连接状态显示和关于信息
16. 增加历史持久化功能
17. 增加清空会话历史功能
18. 使用QWebEngineView重构实现HistoryWidget
19. 添加文本分段器BaseSegmenter
20. 实现普通文本、Markdown和Python分段器
21. C++代码分段器
22. 增加通用代码章节分割函数pack_section
23. 添加向量化数据库BaseVector
24. 添加ChromaDB支持
25. 针对CTP API开发的RAG基础Demo
26. 整理新的代码开发示例目录
