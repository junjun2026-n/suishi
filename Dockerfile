# ============================================================
# 文件名称：Dockerfile
# 生成日期：2026-11-21
# 修改日期：2026-11-21
# 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。
# 文件功能用途：构建邃室 Python 服务容器镜像。
# 注意事项：以非特权用户启动，运行数据需挂载持久卷。
# ============================================================
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py run.py analysis.py decoys.py simulations.py forwarding.py database.py accounts.py ./
COPY static ./static
RUN useradd --uid 10001 --create-home suishi && mkdir runtime && chown suishi:suishi runtime
USER suishi
EXPOSE 8910 8911
CMD ["python", "run.py"]
