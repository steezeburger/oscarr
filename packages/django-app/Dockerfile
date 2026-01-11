FROM python:3.11.4-slim as base
ENV PYTHONUNBUFFERED 1

# install uv and compilation dependencies
# https://cryptography.io/en/latest/installation/
RUN apt-get update && apt-get install -y build-essential libssl-dev libffi-dev python3-dev cargo curl
RUN pip install --upgrade pip
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# install python dependencies
RUN mkdir /code
WORKDIR /code
COPY pyproject.toml uv.lock /code/
RUN uv sync --frozen

# install application into container
COPY . /code

# add virtual environment to PATH
ENV PATH="/code/.venv/bin:$PATH"

# make directories for our logs and backups
RUN mkdir -p /logs
RUN mkdir -p /backups

# run application
EXPOSE 8000

WORKDIR /code/app

# this CMD is overridden by the command in docker-compose.yml for local development
CMD /code/bin/wait-for-it.sh db:5432 -- python /code/app/manage.py runserver 0.0.0.0:8000
