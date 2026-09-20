FROM python:3.13-slim AS build

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.13-slim

RUN groupadd --system pyinfinity \
    && useradd --system --gid pyinfinity --home-dir /app pyinfinity \
    && mkdir -p /data \
    && chown pyinfinity:pyinfinity /data

COPY --from=build /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

USER pyinfinity
WORKDIR /app
EXPOSE 3000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import json,os,urllib.request; c=json.load(open(os.getenv('PY_INFINITY_CONFIG','/config/py-infinity.json'))); p=c['server'].get('listen_port',3000); urllib.request.urlopen(f'http://127.0.0.1:{p}/healthz',timeout=2)"]

ENTRYPOINT ["py-infinity"]
