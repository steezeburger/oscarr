# Oscarr

Oscarr is a Discord bot that connects to Plex and Ombi to provide a Discord
interface for managing media requests.

![](docs/example-breen-machine.png?raw=true)

## Usage

* `/search_tmdb the matrix` - search for a movie on TMDB
  * the results will have buttons at the bottom for the users to request the
    movie
* `/request 603` - request a movie from TMDB using the TMDB ID if having trouble
  finding via search
  * e.g. The Matrix has a TMDB url
    of <https://www.themoviedb.org/movie/603-the-matrix>. \
    The TMDB ID is `603`
* `/search_plex`
  * `/search_plex title: the matrix` - search for a movie on the Plex server
  * `/search_plex all: keanu` - search for a movie by any field
  * `/search_plex actor: keanu reeves` - search for a movie by actor
  * `/search_plex director: tom` - search for a movie by director
  * `/search_plex producer: tom` - search for a movie by producer
* `/get_random` - get random movie from the Plex server
* `/genre_pie` -
* `/bacon from: keanu reeves to: nicolas cage` - show the hops between actors in
  movies that are on the Plex server

## Components

* `packages/django-app` - Django app that provides admin interface for managing
  the data for this bot
* `packages/django-app/app/discordbot` - Discord bot code

## Dependencies

* docker
* docker-compose
* just - https://github.com/casey/just
  * `brew install just` for mac os

## Docker Compose setup

```sh
cd packages/django-app

# you will need to populate env.
# see an example in `.env.template`
touch .env

# init volumes and images. bring up db container.
just init-dcp

# generate secret keys and add to .env
just dcp-generate-secret-key
just generate-pg-secret-key

# can now migrate database
just dcp-migrate

# create superuser
just create-superuser
# OR can load fixture data and login with admin:password
just dcp-load-dev-data

# bring up web container
just dcp-up-all

# open up admin app and login as superuser you just created
# for mac os
open http://0.0.0.0:8000/admin

# start bot in detached container
just dcp-start-bot
```

## helpful scripts

* `./bin/dcp-django-admin.sh`
  * runs `manage.py` in the docker container with argument passthrough
  * `./bin/dcp-django-admin.sh makemigrations`
  * `./bin/dcp-django-admin.sh migrate`
  * `./bin/dcp-django-admin.sh startapp payments`
* `./utils/reload-docker-db.sh` - BROKEN?
  * reloads `dev_data.json` by default
  * `./utils/reload-docker-db.sh --data=fixture_filename.json`
