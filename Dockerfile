FROM python:3.11-slim

WORKDIR /app

COPY ./app/reequirements.txt .

RUN pip install -r requirements.txt

COPY ./app .

EXPOSE 8123

CMD [ "python3", "server.py" ]