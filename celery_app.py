"""Celery application instance - shared across app and tasks."""
from celery import Celery

# Shared Celery instance
celery = Celery('sayhello')
