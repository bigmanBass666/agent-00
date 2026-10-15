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
# 教材路径（换教材只改这里）
# ---------------------------------------------------------------
PDF_PATH = "textbook.pdf"

# ---------------------------------------------------------------
# 知识库输出路径
# ---------------------------------------------------------------
VECTORS_PATH = "kb_vectors.npy"
CHUNKS_PATH = "kb_chunks.json"

# ---------------------------------------------------------------
# 分块参数
# ---------------------------------------------------------------
CHUNK_CHARS = 3500       # 每块约 3500 英文字符 ≈ 800-1000 tokens
CHUNK_OVERLAP = 300      # 块间重叠字符
MIN_CHUNK_CHARS = 200    # 过短的块合并到前一块

# ---------------------------------------------------------------
# 检索参数
# ---------------------------------------------------------------
RECALL_N = 20            # embedding 粗召回候选数
TOP_K = 3                # reranker 精排后喂 LLM 的块数
REFUSE_THRESHOLD = 0.3   # 拒答阈值（换教材后用 calibrate_threshold.py 校准）

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
    raise RuntimeError(
        "未找到 API key。请设置环境变量 SILICONFLOW_API_KEY，"
        "或在脚本同目录创建 .env 文件，写入：SILICONFLOW_API_KEY=你的key"
    )


API_KEY = load_api_key()
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
