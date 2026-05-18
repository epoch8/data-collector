VERSION=0.0.2
REPOSITORY=cr.yandex/crp9t7k628nhsnjetke5
WEB_IMAGE=${REPOSITORY}/cow-web-app
BRANCH=$(shell git rev-parse --abbrev-ref HEAD)

FLUTTER_VERSION=3.41.9
API_BASE_URL=https://data-collector-app.korovas.ml.epoch8.dev


ifeq ($(BRANCH), master)
    FINAL_VERSION := ${VERSION}
else
    FINAL_VERSION := ${VERSION}-$(BRANCH)
endif


build-web:
	docker build -t ${WEB_IMAGE}:${FINAL_VERSION} \
	--build-arg FLUTTER_VERSION=${FLUTTER_VERSION} \
	--build-arg API_BASE_URL=${API_BASE_URL} \
	--ssh default \
	--platform=linux/amd64 . 

upload-web:
	docker push ${WEB_IMAGE}:${FINAL_VERSION}