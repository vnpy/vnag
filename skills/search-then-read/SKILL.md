---
name: search-then-read
description: 针对需要外部或最新信息的问题，先搜索候选来源，再阅读正文并交叉验证。适用于新闻动态、版本发布、政策更新、官方文档确认和事实核查。
---

# 先搜索再阅读

## 适用场景

当任务依赖外部或最新信息时使用本技能，包括：

- 查询近期事实、版本发布、政策更新、价格变动或新闻动态
- 需要引用来源或提供链接的回答
- 需要确认文档、接口行为或产品说明
- 不能只凭模型记忆回答的事实核查问题

如果答案已经可以完全从当前对话、本地文件或已有工具结果中得到，就不要为了形式再联网搜索。

## 前置工具

推荐启用以下工具：

- 主路径：
  - `search-tools_search-web`
  - `search-tools_search-and-read`
- `web-tools_fetch-markdown`

- 可选的高级 / 调试搜索工具：
  - `search-tools_serper-search`
  - `search-tools_tavily-search`
  - `search-tools_jina-search`
  - `search-tools_bocha-search`

如果当前 Profile 没有启用上述工具，应先明确告知用户缺少哪些工具，并建议切换到已启用搜索与网页阅读工具的 Profile，或修改当前 Profile 配置后再继续。

## 工作流

1. 默认优先调用 `search-tools_search-web`，不要直接凭记忆作答。
2. 如果任务明显需要“先搜再直接读正文”，优先考虑 `search-tools_search-and-read` 以减少多步编排失败。
3. 浏览搜索结果或组合工具返回的正文，挑选 5 到 10 个高相关且看起来可信的来源。
4. 对关键链接继续调用 `web-tools_fetch-markdown` 深读，不要只看 snippet 或一次性抓取的摘要正文。
5. 结论优先基于正文内容，而不是搜索结果摘要。
6. 重要事实尽量交叉验证多个来源。
7. 如果来源冲突，明确写出冲突点，并说明你更相信哪一个来源以及理由。
8. 如果结果不充分或明显跑题，调整关键词后重新搜索。

## provider 选择建议

- `search-tools_search-web` 的 `provider` 通常无需显式指定；在 `auto` 模式下会优先尝试当前可用的搜索 provider，并在必要时回退到其他可用 provider。
- 只有在以下情况时，才建议显式指定 provider 或退回使用 raw provider：
  - 需要特定 provider 参数，例如地域、时效性或搜索深度
  - 想比较不同 provider 的结果差异
  - 统一入口结果明显不足，且需要手动兜底

## 输出要求

- 在最终回答中给出使用过的来源。
- 区分“已确认事实”和“基于现有信息的推断”。
- 不确定时明确说明不确定，不要假装已经核实。
- 不要声称某个来源支持某结论，除非正文里确实能找到对应依据。
