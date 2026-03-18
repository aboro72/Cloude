#!/usr/bin/env bash
set -euo pipefail

cd /home/storage/Cloude/cloudservice
/home/storage/Cloude/venv/bin/python manage.py reset_demo_password
