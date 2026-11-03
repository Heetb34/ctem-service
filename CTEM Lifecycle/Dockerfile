FROM python:3.12-slim

WORKDIR /app

COPY ["CTEM Lifecycle/requirements.txt", "./requirements.txt"]
RUN pip install --no-cache-dir -r requirements.txt

COPY ["CTEM Lifecycle/app", "./app"]

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
