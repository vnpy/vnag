API 参考
========

本节提供 VNAG 所有公开模块和类的详细 API 文档。

.. toctree::
   :maxdepth: 2

概述
----

VNAG 的主要模块结构如下：

- ``vnag.agent`` - 智能体模块
- ``vnag.engine`` - 引擎模块
- ``vnag.gateway`` - 网关基类
- ``vnag.gateways`` - 网关实现
- ``vnag.object`` - 数据对象
- ``vnag.constant`` - 常量定义
- ``vnag.local`` - 本地工具
- ``vnag.mcp`` - MCP 工具
- ``vnag.embedder`` - 嵌入器基类
- ``vnag.embedders`` - 嵌入器实现
- ``vnag.segmenter`` - 分段器基类
- ``vnag.segmenters`` - 分段器实现
- ``vnag.vector`` - 向量库基类
- ``vnag.vectors`` - 向量库实现
- ``vnag.tracer`` - 追踪器
- ``vnag.utility`` - 工具函数

vnag
----

.. automodule:: vnag
   :members:
   :show-inheritance:

vnag.agent
----------

.. automodule:: vnag.agent
   :members:
   :show-inheritance:

vnag.engine
-----------

.. automodule:: vnag.engine
   :members:
   :show-inheritance:

vnag.gateway
------------

.. automodule:: vnag.gateway
   :members:
   :show-inheritance:

vnag.object
-----------

.. automodule:: vnag.object
   :members:
   :show-inheritance:

vnag.constant
-------------

.. automodule:: vnag.constant
   :members:
   :show-inheritance:

vnag.local
----------

.. automodule:: vnag.local
   :members:
   :show-inheritance:

vnag.mcp
--------

.. automodule:: vnag.mcp
   :members:
   :show-inheritance:

vnag.tracer
-----------

.. automodule:: vnag.tracer
   :members:
   :show-inheritance:

vnag.utility
------------

.. automodule:: vnag.utility
   :members:
   :show-inheritance:

网关实现
--------

vnag.gateways.openai_gateway
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.gateways.openai_gateway
   :members:
   :show-inheritance:

vnag.gateways.anthropic_gateway
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.gateways.anthropic_gateway
   :members:
   :show-inheritance:

vnag.gateways.deepseek_gateway
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.gateways.deepseek_gateway
   :members:
   :show-inheritance:

vnag.gateways.litellm_gateway
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.gateways.litellm_gateway
   :members:
   :show-inheritance:

嵌入器实现
----------

vnag.embedders.openai_embedder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.embedders.openai_embedder
   :members:
   :show-inheritance:

vnag.embedders.sentence_embedder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.embedders.sentence_embedder
   :members:
   :show-inheritance:

分段器实现
----------

vnag.segmenters.simple_segmenter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.segmenters.simple_segmenter
   :members:
   :show-inheritance:

vnag.segmenters.markdown_segmenter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.segmenters.markdown_segmenter
   :members:
   :show-inheritance:

vnag.segmenters.python_segmenter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.segmenters.python_segmenter
   :members:
   :show-inheritance:

向量库实现
----------

vnag.vectors.chromadb_vector
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.vectors.chromadb_vector
   :members:
   :show-inheritance:

vnag.vectors.qdrant_vector
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vnag.vectors.qdrant_vector
   :members:
   :show-inheritance:

