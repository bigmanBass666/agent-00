# 线上部署说明

> 目的：把 Web UI 部署到公网，方便多设备调试 / 答辩演示
> 支持平台：**Render / Railway / Fly.io**（需能跑 Python 的服务端）
> ❌ **Netlify / Vercel 静态托管不行**——它们只托管静态页面，跑不了 Python 后端

---

## 一、部署前必须知道的三个约束

### 1. 数据文件不在仓库里

`.gitignore` 排除了：

```
kb_chunks.json    # 354 KB，知识库分块（含教材全文）
kb_vectors.npy    # 637 KB，向量矩阵
textbook.pdf      # 56 MB，教材原件
```

云端构建时拿不到这三个文件。三个选项：

| 方案 | 做法 | 代价 |
|------|------|------|
| **A（最简单，推荐用于短周期）** | 临时从 `.gitignore` 移除前两行，把两个数据文件提交 | 教材全文进入 git 历史，**答辩结束后应删除** |
| B | 启动时跑 `build_kb.py` 重建 | 需要把 56 MB 的 PDF 也传上去（版权风险更大），且构建要调 embedding API（约 2 分钟、几百次调用） |
| C | 数据文件放对象存储（OSS/S3），启动时下载 | 最干净，但要额外配存储和公网读权限 |

**本文档按 A 写**，因为课程作业是短周期使用，答辩完即可下线。

### 2. 教材版权

`kb_chunks.json` 内含教材全文。部署到公网 = 全文可被访问。
**建议**：仅在答辩/调试期间部署，结束后**立即删除服务**，不要长期挂着。

### 3. API key

云端必须单独配置环境变量 `SILICONFLOW_API_KEY`，**不要写进代码**。

---

## 二、Render 部署（推荐，免费层够用）

1. 临时放开数据文件：

   ```bash
   # 编辑 .gitignore，注释掉这两行
   # kb_vectors.npy
   # kb_chunks.json

   git add project1/kb_chunks.json project1/kb_vectors.npy
   git commit -m "chore: 临时提交知识库数据用于线上部署"
   git push
   ```

2. Render 控制台 → New → Web Service → 连接本仓库

3. 关键配置：

   | 项 | 值 |
   |---|---|
   | Root Directory | `project1` |
   | Runtime | Python |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `python webui.py` |
   | 环境变量 | `SILICONFLOW_API_KEY` = 你的 key |

   仓库根目录已带 `render.yaml`，也可以直接 New → Blueprint 自动读取。

4. 部署完成后会得到一个 `https://xxx.onrender.com` 地址，手机、平板都能打开。

**注意**：Render 免费层 15 分钟无访问会休眠，首次唤醒要等 30-60 秒。答辩前先访问一次预热。

---

## 三、Railway 部署

1. 同样先提交数据文件（见上文步骤 1）
2. Railway → New Project → Deploy from GitHub repo
3. Settings → Root Directory 填 `project1`
4. Variables 里加 `SILICONFLOW_API_KEY`
5. Railway 会自动识别根目录的 `Procfile`（`web: python webui.py`）和 `requirements.txt`
6. Deploy 后在 Settings → Networking 里 Generate Domain

---

## 四、本地验证（部署前先确认代码没问题）

```bash
cd project1
pip install -r requirements.txt
echo "SILICONFLOW_API_KEY=你的key" > .env
PORT=8000 python webui.py
```

打开 `http://127.0.0.1:8000`，问一句 `How many tablespoons are in one cup?`，应返回：
> 根据教材内容，1杯等于8汤匙【教材 p.14】。

下方应显示 3 个检索片段，第一个是 `[p.14] 表格数据 - UNIT 1  0.4769`。

---

## 五、答辩结束后的清理清单

- [ ] 在 Render/Railway 删除服务（防止教材内容长期公开）
- [ ] `git rm --cached project1/kb_chunks.json project1/kb_vectors.npy` 并恢复 `.gitignore`
- [ ] 若需彻底清除历史，使用 `git filter-repo` 或 BFG 清理（可选）
- [ ] 撤销/轮换暴露过的 API key

---

## 六、为什么不用 Netlify / Vercel 静态托管

| 平台 | 能否跑 Python 后端 | 结论 |
|------|------------------|------|
| Netlify | ❌ 仅静态文件 + Serverless Functions（Node 为主） | 不适合 |
| Vercel | ⚠️ Serverless Functions 支持 Python，但需改造（无长驻进程、无本地文件） | 改造量大，不推荐 |
| **Render / Railway / Fly.io** | ✅ 支持长驻 Python 进程 + 本地文件 | **推荐** |

本项目的 Web UI 依赖：长驻进程（`http.server`）+ 本地 numpy 文件（向量库）。这两个需求与静态托管模型不兼容。
