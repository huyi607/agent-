# ============================================
# Dockerfile - 智扫通机器人智能客服
# 多阶段构建，减小最终镜像体积
# ============================================

# ---- 构建阶段 ----
FROM python:3.13-slim AS builder

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.13-slim

WORKDIR /app

# 从构建阶段复制已安装的 Python 包
COPY --from=builder /root/.local /root/.local

# 确保 PATH 包含用户安装路径
ENV PATH=/root/.local/bin:$PATH

# 复制项目代码
COPY . .

# MODIFIED: 暴露 Streamlit 和 FastAPI 端口
EXPOSE 8501 8000

# 默认启动 Streamlit
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
