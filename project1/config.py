# -*- coding: utf-8 -*-
"""
全局配置
========
换教材时只需修改 PDF_PATH，然后运行：
  1. python build_kb.py      # 重建知识库
  2. python validate_kb.py   # 校验知识库
  3. python run_eval_v2.py   # 跑评测
  4. python calibrate_threshold.py  # 校准阈值（可选）
"""
import os

# ---------------------------------------------------------------
# 教材路径（换教材只改这里；也支持 .epub）
# 用环境变量可让多本书的知识库并存（评测多书时绝不互相覆盖）：
#   BOOK_PATH=evals/econ/book.epub KB_VECTORS=evals/econ/vectors.npy \
#   KB_CHUNKS=evals/econ/chunks.json python build_kb.py
# ---------------------------------------------------------------
PDF_PATH = os.environ.get("BOOK_PATH", "textbook.pdf")

# ---------------------------------------------------------------
# 知识库输出路径（环境变量可覆盖，默认值不变）
# ---------------------------------------------------------------
VECTORS_PATH = os.environ.get("KB_VECTORS", "kb_vectors.npy")
CHUNKS_PATH = os.environ.get("KB_CHUNKS", "kb_chunks.json")

# ---------------------------------------------------------------
# 分块参数
# ---------------------------------------------------------------
CHUNK_CHARS = 3500       # 每块约 3500 英文字符 ≈ 800-1000 tokens
CHUNK_OVERLAP = 300      # 块间重叠字符
MIN_CHUNK_CHARS = 200    # 过短的块合并到前一块
CHUNK_TARGET_MIN = int(os.environ.get("CHUNK_TARGET_MIN", "200"))
# 章节切换时的最小块长阈值：默认 200（章节优先，一菜一块）；
# 设为 3200 则跨章节合并，逼近 800 tokens/块（对比实验用）

# ---------------------------------------------------------------
# 检索参数
# ---------------------------------------------------------------
RECALL_N = 20            # embedding 粗召回候选数
TOP_K = 3                # reranker 精排后喂 LLM 的块数
REFUSE_THRESHOLD = 0.3   # 拒答阈值（换教材后用 calibrate_threshold.py 校准）
HYBRID_RECALL = os.environ.get("HYBRID_RECALL", "1") != "0"  # 设为 0 可关闭词汇召回（对比实验用）

# ---------------------------------------------------------------
# 模型配置（SiliconFlow 免费层）
# ---------------------------------------------------------------
EMBED_URL = "https://api.siliconflow.cn/v1/embeddings"
RERANK_URL = "https://api.siliconflow.cn/v1/rerank"
LLM_URL = "https://api.siliconflow.cn/v1/chat/completions"
EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
LLM_MODEL = "Qwen/Qwen3-8B"

# ---------------------------------------------------------------
# API 配置
# ---------------------------------------------------------------
BATCH_SIZE = 32
TIMEOUT = 60


def load_api_key():
    """从环境变量 SILICONFLOW_API_KEY 或同目录 .env 文件读取"""
    key = os.environ.get("SILICONFLOW_API_KEY")
    if key:
        return key.strip()
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("SILICONFLOW_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    print("[警告] 未找到 API key：离线检查（文件/一致性/元数据）仍可用，"
          "涉及模型调用的步骤请先配置 .env 或环境变量 SILICONFLOW_API_KEY")
    return ""


API_KEY = load_api_key()
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
