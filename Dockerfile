FROM python:3.12.5-slim
EXPOSE 5000

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/
CMD [ "sh", "-c", "python scripts/init_db.py && flask run --host 0.0.0.0" ]