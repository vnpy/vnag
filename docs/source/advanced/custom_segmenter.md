# 自定义分段器

本教程介绍如何创建自定义分段器以支持新的文档格式。

## 分段器接口

分段器需要实现以下接口：

```python
from typing import Any

from vnag.object import Segment
from vnag.segmenter import BaseSegmenter


class BaseSegmenter:
    def parse(self, text: str, metadata: dict[str, Any]) -> list[Segment]:
        """将文本解析并切分为 Segment 列表。"""
        raise NotImplementedError
```

## Segment 结构

```python
from vnag.object import Segment

segment = Segment(
    text="片段文本内容",
    metadata={
        "source": "file.md",
        "section": "第一章",
        "type": "paragraph"
    },
    score=0.0  # 检索时填充
)
```

## 示例：JSON 分段器

```python
import json
from vnag.object import Segment


class JsonSegmenter:
    """JSON 文档分段器
    
    将 JSON 文档按照键值对切分。
    """
    
    def __init__(self, max_depth: int = 2):
        """
        Args:
            max_depth: 最大展开深度
        """
        self.max_depth = max_depth
    
    def parse(self, text: str, metadata: dict[str, Any]) -> list[Segment]:
        """切分 JSON 文档"""
        data = json.loads(text)
        segments = []
        
        self._process_value(
            data, 
            path="", 
            depth=0, 
            segments=segments,
            base_metadata=metadata
        )
        
        return segments
    
    def _process_value(
        self, 
        value, 
        path: str, 
        depth: int, 
        segments: list[Segment],
        base_metadata: dict
    ):
        """递归处理 JSON 值"""
        if depth >= self.max_depth:
            # 达到最大深度，直接序列化
            text = json.dumps(value, ensure_ascii=False, indent=2)
            segments.append(Segment(
                text=f"{path}: {text}" if path else text,
                metadata={
                    **base_metadata,
                    "path": path,
                    "type": str(type(value).__name__)  # 值必须是字符串
                }
            ))
            return
        
        if isinstance(value, dict):
            for key, val in value.items():
                new_path = f"{path}.{key}" if path else key
                self._process_value(
                    val, new_path, depth + 1, segments, base_metadata
                )
        elif isinstance(value, list):
            for i, item in enumerate(value):
                new_path = f"{path}[{i}]"
                self._process_value(
                    item, new_path, depth + 1, segments, base_metadata
                )
        else:
            # 基本类型
            segments.append(Segment(
                text=f"{path}: {value}",
                metadata={
                    **base_metadata,
                    "path": path,
                    "type": str(type(value).__name__)  # 值必须是字符串
                }
            ))
```

### 使用示例

```python
segmenter = JsonSegmenter(max_depth=2)

content = '''
{
    "name": "VNAG",
    "version": "0.6.0",
    "features": {
        "agent": "TaskAgent 支持",
        "tools": ["本地工具", "MCP 工具"]
    }
}
'''

segments = segmenter.parse(content, metadata={"source": "config.json"})

for seg in segments:
    print(f"路径: {seg.metadata.get('path')}")
    print(f"内容: {seg.text}")
    print()
```

## 示例：HTML 分段器

```python
from html.parser import HTMLParser
from vnag.object import Segment


class HtmlSegmenter:
    """HTML 文档分段器
    
    按照段落和标题切分 HTML 文档。
    """
    
    def __init__(self, min_length: int = 50):
        """
        Args:
            min_length: 片段最小长度
        """
        self.min_length = min_length
    
    def parse(self, text: str, metadata: dict[str, Any]) -> list[Segment]:
        """切分 HTML 文档"""
        parser = _HtmlContentParser()
        parser.feed(text)
        
        segments = []
        current_heading = ""
        
        for item in parser.items:
            if item["type"] == "heading":
                current_heading = item["text"]
            elif item["type"] == "text":
                text = item["text"].strip()
                if len(text) >= self.min_length:
                    segments.append(Segment(
                        text=text,
                        metadata={
                            **metadata,
                            "heading": current_heading,
                            "tag": item.get("tag", "p")
                        }
                    ))
        
        return segments


class _HtmlContentParser(HTMLParser):
    """HTML 内容解析器"""
    
    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    TEXT_TAGS = {"p", "div", "span", "li", "td", "th"}
    
    def __init__(self):
        super().__init__()
        self.items = []
        self.current_tag = ""
        self.current_text = ""
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()
        self.current_text = ""
    
    def handle_data(self, data):
        self.current_text += data
    
    def handle_endtag(self, tag):
        tag = tag.lower()
        text = self.current_text.strip()
        
        if not text:
            return
        
        if tag in self.HEADING_TAGS:
            self.items.append({
                "type": "heading",
                "text": text,
                "level": int(tag[1])
            })
        elif tag in self.TEXT_TAGS:
            self.items.append({
                "type": "text",
                "text": text,
                "tag": tag
            })
```

## 示例：YAML 分段器

```python
import yaml
from vnag.object import Segment


class YamlSegmenter:
    """YAML 文档分段器"""
    
    def parse(self, text: str, metadata: dict) -> list[Segment]:
        """切分 YAML 文档"""
        # 支持多文档 YAML
        documents = list(yaml.safe_load_all(text))
        segments = []
        
        for doc_idx, doc in enumerate(documents):
            if doc is None:
                continue
            
            self._process_dict(
                doc,
                path="",
                doc_index=doc_idx,
                segments=segments,
                base_metadata=metadata
            )
        
        return segments
    
    def _process_dict(
        self, 
        data: dict, 
        path: str,
        doc_index: int,
        segments: list[Segment],
        base_metadata: dict
    ):
        """处理字典"""
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                self._process_dict(
                    value, current_path, doc_index, segments, base_metadata
                )
            elif isinstance(value, list):
                text = yaml.dump(
                    {key: value}, 
                    allow_unicode=True, 
                    default_flow_style=False
                )
                segments.append(Segment(
                    text=text,
                    metadata={
                        **base_metadata,
                        "path": current_path,
                        "doc_index": str(doc_index),  # 值必须是字符串
                        "type": "list"
                    }
                ))
            else:
                segments.append(Segment(
                    text=f"{key}: {value}",
                    metadata={
                        **base_metadata,
                        "path": current_path,
                        "doc_index": str(doc_index),  # 值必须是字符串
                        "type": str(type(value).__name__)  # 值必须是字符串
                    }
                ))
```

## 设计建议

### 1. 保持上下文

片段应包含足够的上下文信息：

```python
# 不好：只有内容
segment = Segment(text="安装命令是 pip install vnag")

# 好：包含上下文
segment = Segment(
    text="## 安装\n\n安装命令是 pip install vnag",
    metadata={"section": "安装指南"}
)
```

### 2. 控制片段大小

片段不宜过大或过小：

```python
def parse(self, text: str, metadata: dict):
    segments = []
    
    for chunk in self._split(text):
        # 过滤过短的片段
        if len(chunk) < self.min_length:
            continue
        
        # 拆分过长的片段
        if len(chunk) > self.max_length:
            for sub_chunk in self._split_long(chunk):
                segments.append(Segment(text=sub_chunk, ...))
        else:
            segments.append(Segment(text=chunk, ...))
    
    return segments
```

### 3. 丰富的元数据

添加有助于过滤和展示的元数据（注意：所有值必须是字符串类型）：

```python
segment = Segment(
    text=content,
    metadata={
        "source": file_path,
        "section": section_title,
        "type": content_type,
        "language": language,
        "line_start": str(line_number),  # 数值需转换为字符串
        "created_at": timestamp
    }
)
```

### 4. 错误处理

妥善处理格式错误：

```python
def parse(self, text: str, metadata: dict):
    try:
        data = parse(text)
        return self._process(data, metadata)
    except ParseError as e:
        # 返回整个内容作为单个片段
        return [Segment(
            text=text,
            metadata={
                **metadata,
                "parse_error": str(e)
            }
        )]
```

## 下一步

- [思维链集成](thinking.md) - 利用模型的思考过程
- [RAG 模块](../rag/index.md) - 在 RAG 中使用分段器

