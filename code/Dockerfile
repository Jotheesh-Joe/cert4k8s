FROM python:3.9-slim

LABEL maintainer="Jotheeswaran Lakshmanan"

WORKDIR /usr/app/src

COPY app.py ./

COPY requirements.txt ./

RUN pip install -r ./requirements.txt

CMD ["python", "-u", "./app.py"]

