VERSION=0.0.17
IMAGE=cr.yandex/crp9t7k628nhsnjetke5/cow-data-collector
BRANCH=$(shell git rev-parse --abbrev-ref HEAD)

ifeq ($(BRANCH), master)
    FINAL_VERSION := ${VERSION}
else
    FINAL_VERSION := ${VERSION}-$(BRANCH)
endif


build:
	docker build -t ${IMAGE}:${FINAL_VERSION} --progress=plain --ssh default --platform=linux/amd64 . 

upload:
	docker push ${IMAGE}:${FINAL_VERSION}