FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install gunicorn

COPY . .

EXPOSE 8101

CMD ["gunicorn", "gptchatbot.wsgi:application", "--bind", "0.0.0.0:8101"]
