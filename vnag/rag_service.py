from typing import Generator

from .document_service import DocumentService
from .gateway import AgentGateway
from .vector_service import VectorService


RAG_PROMPT_TEMPLATE = """基于以下上下文信息回答用户问题。如果上下文中没有相关信息，请说明无法从提供的文档中找到答案。

上下文信息：
{context}

用户问题：{question}

请基于上下文提供准确的回答："""


class RAGService:
    """RAG消息预处理服务（gateway内部组件）"""

    def __init__(self, gateway) -> None:
        """构造函数"""
        self.gateway = gateway  # 仅用于循环引用，不直接调用
        self.document_service = DocumentService()
        self.vector_service = VectorService()

        self._init_knowledge_base()

    def _init_knowledge_base(self) -> None:
        """初始化知识库"""
        from .utility import AGENT_DIR
        # docs目录应该与.vnag目录同级
        docs_dir = AGENT_DIR.parent / "docs"
        
        if not docs_dir.exists():
            return
            
        # 只收集md文件，保持简单
        doc_files = list(docs_dir.glob("**/*.md"))
        
        if doc_files and self.vector_service.get_document_count() == 0:
            file_paths = [str(f) for f in doc_files]
            self.add_documents(file_paths)

    def add_documents(self, file_paths: list[str]) -> bool:
        """添加文档到知识库"""
        if not file_paths:
            return False
            
        all_chunks = []
        for file_path in file_paths:
            chunks = self.document_service.process_file(file_path)
            all_chunks.extend(chunks)

        if all_chunks:
            self.vector_service.add_documents(all_chunks)
            return True

        return False

    def _process_user_files(self, user_files: list[str] | None) -> str:
        """处理用户提交的文件（直接读取文本，不做向量化处理）"""
        if not user_files:
            return ""
            
        user_content = ""
        for file_path in user_files:
            try:
                from pathlib import Path
                path = Path(file_path)
                
                # 只支持简单的文本文件，直接读取
                if path.suffix.lower() in ['.md', '.txt']:
                    content = path.read_text(encoding='utf-8')
                    user_content += f"\n\n用户提交文件 {path.name}:\n{content}"
                else:
                    user_content += f"\n\n用户提交文件 {path.name}: (不支持的文件格式)"
            except Exception:
                user_content += f"\n\n用户提交文件 {file_path}: (读取失败)"
                
        return user_content


    def prepare_rag_messages(self, messages: list[dict[str, str]], user_files: list[str] | None = None) -> list[dict[str, str]]:
        """准备RAG增强的消息"""
        if not messages:
            return messages
            
        # 提取最后一个用户问题
        last_message = messages[-1]
        if last_message.get("role") != "user":
            return messages
            
        question = last_message["content"]
        
        # 检索知识库文档
        # k=3: 检索3个最相关文档，平衡回答质量和token消耗
        relevant_docs = self.vector_service.similarity_search(question, k=3)
        
        # 处理用户提交的文件
        user_content = self._process_user_files(user_files)
        
        # 如果既没有知识库文档也没有用户文件，返回原消息
        if not relevant_docs and not user_content:
            return messages
        
        # 构建完整上下文
        context_parts = []
        
        if relevant_docs:
            kb_context = "\n\n".join([
                f"知识库文档 {i+1}:\n{doc['text']}" 
                for i, doc in enumerate(relevant_docs)
            ])
            context_parts.append(kb_context)
        
        if user_content:
            context_parts.append(user_content)
        
        context = "\n\n".join(context_parts)
        
        # 构建RAG prompt
        rag_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context,
            question=question
        )
        
        # 返回处理后的消息
        new_messages = messages[:-1] + [{"role": "user", "content": rag_prompt}]
        
        return new_messages

    def prepare_file_messages(self, messages: list[dict[str, str]], user_files: list[str] | None = None) -> list[dict[str, str]]:
        """只处理用户文件的消息（不使用知识库）"""
        if not messages or not user_files:
            return messages
            
        # 提取最后一个用户问题
        last_message = messages[-1]
        if last_message.get("role") != "user":
            return messages
            
        question = last_message["content"]
        
        # 只处理用户提交的文件
        user_content = self._process_user_files(user_files)
        
        if not user_content:
            return messages
            
        # 将用户文件内容直接加入消息（不使用RAG模板）
        final_question = f"{question}\n\n参考文件内容：{user_content}"
        
        # 返回处理后的消息
        new_messages = messages[:-1] + [{"role": "user", "content": final_question}]
        
        return new_messages

    def get_document_count(self) -> int:
        """获取文档数量"""
        return self.vector_service.get_document_count()

    def clear_documents(self) -> None:
        """清空知识库"""
        self.vector_service.clear_documents()
