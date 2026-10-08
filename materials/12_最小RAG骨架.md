# 最小 RAG 骨架（项目一半成品）

> 本文件由 `12_最小RAG骨架.py` 转换而来，内容为原始 Python 代码。

```python
# -*- coding: utf-8 -*-
"""
最小 RAG 骨架（项目一半成品）
=============================
说明：本文件含 6 处 TODO。全部补完后运行 `python 12_最小RAG骨架.py` 应能完成一次
端到端问答。每个 TODO 上方有提示，对应概念卡编号见注释。
配套语料见 13_样例语料与标准分块.md，先把语料存为 corpus/os_ch1.txt 再运行。
"""

import json
import numpy as np

# ---------------------------------------------------------------
# 配置区（可按需调整，调整需在设计文档中说明理由）
# ---------------------------------------------------------------
CHUNK_SIZE = 500          # 分块大小（字）
CHUNK_OVERLAP = 50        # 块间重叠
TOP_K = 3                 # 检索返回的分块数
REFUSE_THRESHOLD = 0.35   # 拒答阈值：最高相似度低于此值则拒答
DOCS_PATH = "corpus/os_ch1.txt"

# ---------------------------------------------------------------
# TODO 1（卡 7）：实现分块器
# 提示：按空行/标题切优先于硬切；若硬切需处理重叠，防止句子被切断。
# 返回: List[dict]，每个元素 {"chunk_id": int, "text": str, "source": str}
# ---------------------------------------------------------------
def load_and_chunk(path: str):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    chunks = []
    # === TODO 1 START ===
    pass
    # === TODO 1 END ===
    return chunks


# ---------------------------------------------------------------
# TODO 2（卡 4）：实现 embedding
# 课程提供统一 embedding 接口（见环境速通包）。本函数只负责调用并返回向量。
# 若接口不可用，可用本地哈希 trick 暂代：hash 字符 n-gram 统计向量（仅调试用，
# 效果差，必须在文档中声明）。返回: np.ndarray, shape (dim,)
# ---------------------------------------------------------------
def embed(text: str) -> np.ndarray:
    # === TODO 2 START ===
    pass
    # === TODO 2 END ===


# ---------------------------------------------------------------
# TODO 3（卡 5）：实现检索
# 提示：对全部分块向量计算余弦相似度，返回 top_k 个 (chunk, score)。
# 几千规模用 numpy 暴力即可，无需向量数据库（工程选型跟数据规模走）。
# ---------------------------------------------------------------
def retrieve(query: str, chunks, top_k=TOP_K):
    # === TODO 3 START ===
    pass
    # === TODO 3 END ===


# ---------------------------------------------------------------
# TODO 4（卡 3 + 卡 8）：组装 Prompt 并调用 LLM
# 系统指令要点：只能依据给定资料回答；资料不足时输出固定拒答句；
# 回答后注明来源 chunk_id。返回: str
# ---------------------------------------------------------------
SYSTEM_PROMPT = (
    "你是课程助教。你只能依据【资料】回答，不得编造。"
    "若资料不足以回答，必须只输出：课程资料中未找到相关内容。"
    "回答末尾注明来源段落编号。"
)
REFUSE_SENTENCE = "课程资料中未找到相关内容。"


def answer(query: str, retrieved) -> str:
    if not retrieved:
        return REFUSE_SENTENCE
    # === TODO 4 START ===
    # 1) 将 retrieved 中的 chunk 文本拼入 Prompt 的【资料】部分
    # 2) 调用课程统一 LLM 接口（勿用个人 key）
    # 3) 返回模型输出
    pass
    # === TODO 4 END ===


# ---------------------------------------------------------------
# TODO 5（卡 8）：拒答判定
# 若 top-1 相似度 < REFUSE_THRESHOLD，直接拒答，不调用 LLM。
# 为什么放在 LLM 之前？（答案写进你的设计文档）
# ---------------------------------------------------------------
def rag_query(query: str, chunks) -> dict:
    retrieved = retrieve(query, chunks)
    # === TODO 5 START ===
    pass
    # === TODO 5 END ===
    # 返回格式: {"query":..., "answer":..., "refused": bool,
    #            "sources": [chunk_id,...], "top_score": float}


# ---------------------------------------------------------------
# TODO 6：主流程
# 运行后应输出一次完整问答（含来源与是否拒答），供你确认链路打通。
# ---------------------------------------------------------------
if __name__ == "__main__":
    chunks = load_and_chunk(DOCS_PATH)
    print(f"共加载 {len(chunks)} 个分块")
    result = rag_query("什么是进程？进程和程序有什么区别？", chunks)
    # === TODO 6 START ===
    pass
    # === TODO 6 END ===
```
