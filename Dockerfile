FROM python:3.11-slim

WORKDIR /app

COPY ./app/requirements.txt .

RUN pip install -r requirements.txt

COPY ./app .

EXPOSE 8123

CMD [ "python3", "server.py" ]

# docker build -t "docker username"/"name of your project":latest . to build the image
# docker run -p 8000:8000 --env-file ./app/.env "docker username"/"name of your project":latest to run the container
# docker push "docker username"/"name of your project":latest to push the image to docker hub