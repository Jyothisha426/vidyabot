FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data static

EXPOSE 7860

ENV FLASK_ENV=production

CMD ["python", "app_cloud.py"]
