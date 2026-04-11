FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["streamlit", "run", "chatbot-ui-bir-streamed.py", "--server.address=0.0.0.0", "--server.port=8001"]
