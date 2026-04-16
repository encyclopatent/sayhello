"""Celery application instance - shared across app and tasks."""
import os
from dotenv import load_dotenv
from celery import Celery

# Load environment variables
load_dotenv()

# Configure Redis connection
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', 6379)
redis_password = os.environ.get('REDIS_PASSWORD', '')
redis_db = os.environ.get('REDIS_DB', 0)

redis_url = f'redis://'
if redis_password:
    redis_url += f':{redis_password}@'
redis_url += f'{redis_host}:{redis_port}/{redis_db}'

# Shared Celery instance with Redis configuration
celery = Celery(
    'sayhello',
    broker=redis_url,
    backend=redis_url
)

# Celery configuration
celery.conf.update(
    broker_pool_limit=10,
    broker_heartbeat=30,
    broker_connection_timeout=20,
    result_backend_max_retries=3,
    result_backend_retry_interval=1,
)

# Auto-discover and import tasks
# Import tasks module to register them with the worker
import tasks
import sirna_analysis
