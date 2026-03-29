#!/usr/bin/env bash
# Exit on error
set -o errexit

# Upgrade pip and key build tools
pip install --upgrade pip
pip install setuptools==69.5.1 wheel

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Automatically populate songs from media/songs directory
python manage.py populate_songs

# Automatically create superuser if environment variables are set
python manage.py createsuperuser --noinput || true
