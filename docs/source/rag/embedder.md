# Embedder 嵌入器

嵌入器负责把文本转换为向量表示，是 RAG 的核心组件之一。

## BaseEmbedder 基类

VNAG 的嵌入器统一接口是 `encode()`：

```python
from vnag.embedder import BaseEmbedder


class BaseEmbedder:
    def encode(self, texts: list[str]):
        """将文本列表编码为向量（返回 numpy.ndarray）。"""
        raise NotImplementedError
```

调用方式：

```python
embeddings = embedder.encode(["文本1", "文本2"])
print(embeddings.shape)  # (2, dim)
```

## OpenaiEmbedder

`OpenaiEmbedder` 使用 OpenAI 兼容的 Embeddings 接口（由 OpenAI Python SDK 调用）。

```python
from vnag.embedders.openai_embedder import OpenaiEmbedder
from vnag.utility import load_json

setting = load_json("connect_openai.json")
embedder = OpenaiEmbedder(
    api_key=setting["api_key"],
    base_url=setting["base_url"],
    model_name="text-embedding-3-small",
)

vec = embedder.encode(["这是一段测试文本"])[0]
print(len(vec))
```

## DashscopeEmbedder

`DashscopeEmbedder` 使用阿里云 DashScope 的 Embeddings 接口。

```python
from vnag.embedders.dashscope_embedder import DashscopeEmbedder
from vnag.utility import load_json

setting = load_json("connect_dashscope.json")
embedder = DashscopeEmbedder(
    api_key=setting["api_key"],
    model_name="text-embedding-v3",
)

vec = embedder.encode(["测试文本"])[0]
print(len(vec))
```

## SentenceEmbedder

`SentenceEmbedder` 使用本地 `sentence-transformers`，无需 API Key。

```python
from vnag.embedders.sentence_embedder import SentenceEmbedder

embedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
vec = embedder.encode(["测试文本"])[0]
print(len(vec))
```

安装依赖：

```bash
pip install sentence-transformers
```

## 使用建议

- **一致性**：索引和查询必须使用同一个 embedder（以及同一个模型），否则向量空间不一致会导致检索质量严重下降。
- **批量调用**：优先一次性 `encode(list[str])`，比循环单条更高效。


