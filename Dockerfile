FROM ubuntu AS build

ARG FLUTTER_VERSION="3.41.9"
ARG API_BASE_URL=""

RUN apt-get update
RUN apt-get install -y curl git unzip
RUN git clone --depth 1 --branch "${FLUTTER_VERSION}" https://github.com/flutter/flutter.git
ENV PATH="/flutter/bin:${PATH}"

COPY . /app
WORKDIR /app
RUN flutter clean
RUN flutter pub get
RUN flutter build web --release --dart-define=API_BASE_URL=${API_BASE_URL}

FROM nginx
COPY --from=build /app/build/web /usr/share/nginx/html