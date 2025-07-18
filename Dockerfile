FROM python:3.10-slim
WORKDIR /app
COPY app /app/app
RUN pip install --no-cache-dir fastapi uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
