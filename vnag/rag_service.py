from pathlib import Path

from .document_service import DocumentService
from .vector_service import VectorService
from .utility import TEMP_DIR
from .template import RAG_PROMPT_TEMPLATE, CHAT_PROMPT_TEMPLATE


class RAGService:
    """RAG消息预处理服务（gateway内部组件）"""

    def __init__(self) -> None:
        """构造函数"""
        self.document_service = DocumentService()
        self.vector_service = VectorService()

        self._init_knowledge_base()

    def _init_knowledge_base(self) -> None:
        """初始化知识库"""
        # docs目录位于 .vnag 目录内
        docs_dir: Path = TEMP_DIR / "docs"

        if not docs_dir.exists():
            return

        # 只收集md文件，保持简单
        doc_files: list = list(docs_dir.glob("**/*.md"))

        if doc_files and self.vector_service.get_document_count() == 0:
            file_paths: list = [str(f) for f in doc_files]
            self.add_documents(file_paths)

    def add_documents(self, file_paths: list[str]) -> bool:
        """添加文档到知识库"""
        if not file_paths:
            return False

        all_chunks: list = []
        total: int = len(file_paths)
        for idx, file_path in enumerate(file_paths, start=1):
            print(f"[RAG] 导入进度 {idx}/{total}: {Path(file_path).name}")
            chunks: list = self.document_service.process_file(file_path)
            all_chunks.extend(chunks)

        if all_chunks:
            self.vector_service.add_documents(all_chunks)
            return True

        return False

    def _process_user_files(self, user_files: list[str] | None) -> str:
        """处理用户提交的文件：统一使用 DocumentService.read_file_text 读取原文。"""
        if not user_files:
            return ""

        user_content: str = ""
        for file_path in user_files:
            try:
                path: Path = Path(file_path)
                content: str = self.document_service.read_file_text(str(path))
                user_content += f"\n\n用户提交文件 {path.name}:\n{content}"
            except ValueError:
                # 不支持的文件格式
                path = Path(file_path)
                user_content += f"\n\n用户提交文件 {path.name}: (不支持的文件格式)"
            except Exception:
                user_content += f"\n\n用户提交文件 {file_path}: (读取失败)"

        return user_content

    def prepare_rag_messages(
        self,
        messages: list[dict[str, str]],
        user_files: list[str] | None = None
    ) -> list[dict[str, str]]:
        """准备RAG增强的消息"""
        if not messages:
            return messages

        # 提取最后一个用户问题
        last_message: dict = messages[-1]
        if last_message.get("role") != "user":
            return messages

        question: str = last_message["content"]

        # 检索知识库文档
        # k=3: 检索3个最相关文档，平衡回答质量和token消耗
        relevant_docs: list = self.vector_service.similarity_search(
            question,
            k=3,
        )

        # 处理用户提交的文件
        user_content: str = self._process_user_files(user_files)

        # 如果既没有知识库文档也没有用户文件，返回原消息
        if not relevant_docs and not user_content:
            return messages

        # 构建完整上下文
        context_parts: list = []

        if relevant_docs:
            kb_context: str = "\n\n".join([
                f"知识库文档 {i+1}:\n{doc['text']}"
                for i, doc in enumerate(relevant_docs)
            ])
            context_parts.append(kb_context)

        context: str = "\n\n".join(context_parts)

        # 构建RAG prompt
        rag_prompt: str = RAG_PROMPT_TEMPLATE.format(
            context=context,
            question=question
        )

        # 若有用户文件，则在模板后追加参考内容（不纳入检索上下文）
        if user_content:
            rag_prompt = f"{rag_prompt}\n\n参考文件内容：{user_content}"

        # 返回处理后的消息
        new_messages: list = messages[:-1] + [
            {"role": "user", "content": rag_prompt}
        ]

        return new_messages

    def prepare_chat_messages(
        self,
        messages: list[dict[str, str]],
        user_files: list[str] | None = None
    ) -> list[dict[str, str]]:
        """非RAG的普通聊天模板包装（无知识库、无用户文件）"""
        if not messages:
            return messages

        last_message: dict = messages[-1]
        if last_message.get("role") != "user":
            return messages

        question: str = last_message["content"]

        # 使用CHAT模板包装原始问题
        prompt: str = CHAT_PROMPT_TEMPLATE.format(question=question)

        # 若有用户文件，则在模板后追加参考内容
        if user_files:
            user_content: str = self._process_user_files(user_files)
            if user_content:
                prompt = f"{prompt}\n\n参考文件内容：{user_content}"

        new_messages: list = messages[:-1] + [
            {"role": "user", "content": prompt}
        ]
        return new_messages

    def get_document_count(self) -> int:
        """获取文档数量"""
        count: int = self.vector_service.get_document_count()
        return count
