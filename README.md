# Oscarr

* dependencies
  * docker
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
