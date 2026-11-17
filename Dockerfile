# Backend image.
#
# Dependencies are installed in their own layer, before the source is
# copied, so editing a Python file does not re-download every package.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini pyproject.toml ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

# Runs as a non-root user. A container that does not need root should not
# have it — if the app is ever compromised, this is what limits the damage.
RUN useradd --create-home --uid 10001 stockex && chown -R stockex:stockex /srv
USER stockex

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
