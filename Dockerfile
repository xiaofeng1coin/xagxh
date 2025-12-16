FROM python:3.9-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
# 复制依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制其余代码
COPY . .

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "app.py"]
