FROM python:3.12.5-slim
EXPOSE 5000

RUN pip install uv

WORKDIR /app
COPY requirements.lock ./
RUN uv pip install --no-cache --system -r requirements.lock

COPY . /app/
CMD [ "flask", "run", "--host", "0.0.0.0" ]