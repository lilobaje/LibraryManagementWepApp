#!/usr/bin/venv bash

# Exit on error
set -o errexit


# Install dependencies
pip install -r requirements.txt


# Collect static files
python manage.py collectstatic --noinput



