FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# gettext: compilemessages; pango/harfbuzz/fonts: WeasyPrint PDF export
RUN apt-get update && apt-get install -y --no-install-recommends \
        gettext libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ARG UID=1000
RUN useradd --create-home --uid ${UID} app

WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY --chown=app:app . .
USER app

EXPOSE 8000
CMD ["/app/docker/entrypoint.sh"]
