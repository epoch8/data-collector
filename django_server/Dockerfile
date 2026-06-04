FROM node:22-bookworm AS frontend
WORKDIR /build
COPY frontend/packages/package.json frontend/packages/package-lock.json ./
RUN npm ci
COPY frontend/packages/ ./
ENV DJANGO_STATIC_OUT=dist
RUN npm run build

FROM python:3.14-bookworm

RUN mkdir /app
WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
COPY --from=frontend /build/dist /app/api/static/packages

RUN python3 manage.py collectstatic --no-input --clear
