FROM python:3.14-bookworm

RUN mkdir /app
WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app

# RUN python3 manage.py collectstatic --no-input --clear