# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Oscarr is a Discord bot that integrates with Plex and Ombi to provide a Discord interface for managing media requests. The project consists of a Django backend that serves both as an admin interface and the bot's data layer.

## Development Commands

All commands should be run from `/packages/django-app/` directory using the `just` task runner:

### Setup & Initialization
- `just init-dcp` - Initialize Docker volumes and build images
- `just dcp-generate-secret-key` - Generate Django secret key for .env
- `just generate-pg-secret-key` - Generate PostgreSQL encryption key
- `just create-superuser` - Create Django admin user
- `just dcp-load-dev-data` - Load fixture data (admin:password login)

### Development Workflow
- `just dcp-up-all` - Start all containers (web + db)
- `just dcp-migrate` - Run database migrations
- `just start-discord-bot` - Launch Discord bot in container
- `just sync-with-plex` - Sync movie data from Plex server

### Testing & Code Quality
- `just dcp-run-tests` - Run pytest test suite (excludes integration tests)
- `just dcp-format` - Format Python code with autopep8

### Backup & Data Management
- `just dcp-dumpdata` - Export database to JSON
- `just create-json-backup` - Create timestamped JSON backup
- `just create-pgdump` - Create PostgreSQL dump backup

## Architecture

### Django Apps Structure
- `core/` - User management with custom User model, Discord/Ombi integration
- `plex/` - Plex server data models and sync functionality
- `movie_requests/` - Movie request handling commands
- `watchbot/` - Additional bot functionality
- `discordbot/` - Discord bot implementation with commands
- `services/` - External API integrations (Ombi, Radarr, TMDB)

### Key Patterns
- **Repository Pattern**: Base repository classes in `common/repositories/`
- **Management Commands**: Custom Django commands for bot operations and data sync
- **Signal Integration**: Django signals for automated workflows (e.g., Ombi user creation)
- **Encrypted Fields**: Uses django-pgcrypto-fields for sensitive data

### Discord Bot Commands
- `/search_tmdb` - Search TMDB for movies with request buttons
- `/request <tmdb_id>` - Request movie by TMDB ID
- `/search_plex` - Search Plex library (by title, actor, director, producer)
- `/get_random` - Get random movie from Plex
- `/bacon from: <actor1> to: <actor2>` - Show actor connections through movies

## Environment Setup

The project requires a `.env` file in `/packages/django-app/` with configuration for:
- Django secret keys
- PostgreSQL credentials  
- Plex server connection
- Ombi API credentials
- Discord bot token

See `.env.template` for required environment variables.

## Technology Stack

- **Backend**: Django 4.2.5, PostgreSQL 15.4
- **Bot**: discord.py
- **Media APIs**: PlexAPI, TMDB Simple
- **External Services**: Ombi, Radarr
- **Testing**: pytest with Django integration
- **Containerization**: Docker Compose
- **Task Runner**: Just (justfile)
- **Code Quality**: autopep8, pylint, flake8

## Development Notes

- Uses Python 3.11.4 with Pipenv for dependency management
- PostgreSQL with pgcrypto extension for encrypted fields
- All Django management commands should be run via `./bin/dcp-django-admin.sh` for Docker
- Tests exclude integration tests by default (use `-m "not integration"`)
- The bot runs as a separate management command (`start_discord_bot`)
- Plex sync should be run periodically to keep movie data current