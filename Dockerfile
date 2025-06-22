FROM python:3.10-slim
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "app:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "180"]
