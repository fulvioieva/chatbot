FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py knowledge_base.py bot_behavior.py followup_manager.py conversation_manager.py ./

CMD ["python", "app.py"]
