FROM python:3.9-slim

LABEL maintainer="Jotheeswaran Lakshmanan"

WORKDIR /usr/app/src

COPY code/app.py /usr/app/src

COPY code/requirements.txt /usr/app/src

RUN pip install -r ./requirements.txt

CMD ["python", "-u", "./app.py"]

