FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py run.py analysis.py simulations.py forwarding.py database.py accounts.py ./
COPY static ./static
RUN useradd --uid 10001 --create-home suishi && mkdir runtime && chown suishi:suishi runtime
USER suishi
EXPOSE 8910 8911
CMD ["python", "run.py"]
