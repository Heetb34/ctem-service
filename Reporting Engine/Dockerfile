FROM python:3.12-slim

WORKDIR /app

COPY ["Reporting Engine/requirements.txt", "./requirements.txt"]

RUN pip install --no-cache-dir -r requirements.txt

COPY ["Reporting Engine/reporting_engine", "./reporting_engine"]

ENV PYTHONPATH=/app

EXPOSE 8003

CMD ["uvicorn", "reporting_engine.main:app", "--host", "0.0.0.0", "--port", "8003"]
