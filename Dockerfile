FROM ghcr.io/astral-sh/uv AS uv

FROM python:3.12-slim
ARG TARGETARCH
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install chromium -y
RUN if [ "${TARGETARCH}" = "arm64" ] ; then apt-get install chromium-driver -y ; else echo "Skipping" ; fi
COPY pyproject.toml .
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    apt-get -y install gcc musl-dev && \
    uv pip install --system -r pyproject.toml && \
    apt-get -y autoremove gcc musl-dev && apt-get clean
COPY . .
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    uv pip install --system -e .
ENTRYPOINT [ "python", "main.py" ]