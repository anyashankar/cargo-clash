"""Celery application for asynchronous task processing."""

import logging
from celery import Celery
from celery.schedules import crontab

from .config import settings

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "cargo_clash",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        'backend.app.tasks.game_tasks',
        'backend.app.tasks.market_tasks',
        'backend.app.tasks.player_tasks',
        'backend.app.tasks.maintenance_tasks'
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,
    result_persistent=True,
    
    # Task routing
    task_routes={
        'backend.app.tasks.game_tasks.*': {'queue': 'game_events'},
        'backend.app.tasks.market_tasks.*': {'queue': 'market_updates'},
        'backend.app.tasks.player_tasks.*': {'queue': 'player_actions'},
        'backend.app.tasks.maintenance_tasks.*': {'queue': 'maintenance'},
    },
    
    # Periodic tasks
    beat_schedule={
        'update-market-prices': {
            'task': 'backend.app.tasks.market_tasks.update_market_prices',
            'schedule': crontab(minute='*/5'),  # Every 5 minutes
        },
        'process-expired-missions': {
            'task': 'backend.app.tasks.game_tasks.process_expired_missions',
            'schedule': crontab(minute='*/10'),  # Every 10 minutes
        },
        'generate-random-events': {
            'task': 'backend.app.tasks.game_tasks.generate_random_events',
            'schedule': crontab(minute='*/15'),  # Every 15 minutes
        },
        'update-player-rankings': {
            'task': 'backend.app.tasks.player_tasks.update_player_rankings',
            'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
        },
        'cleanup-old-data': {
            'task': 'backend.app.tasks.maintenance_tasks.cleanup_old_data',
            'schedule': crontab(minute=0, hour=2),  # Daily at 2 AM
        },
        'backup-player-data': {
            'task': 'backend.app.tasks.maintenance_tasks.backup_player_data',
            'schedule': crontab(minute=0, hour=3),  # Daily at 3 AM
        },
        'send-daily-metrics': {
            'task': 'backend.app.tasks.maintenance_tasks.send_daily_metrics',
            'schedule': crontab(minute=0, hour=1),  # Daily at 1 AM
        },
    },
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Task annotations for specific configurations
celery_app.conf.task_annotations = {
    'backend.app.tasks.game_tasks.process_combat': {
        'rate_limit': '100/m',  # Max 100 combat processes per minute
        'time_limit': 30,       # 30 second time limit
        'soft_time_limit': 25,  # 25 second soft limit
    },
    'backend.app.tasks.market_tasks.update_market_prices': {
        'rate_limit': '1/m',    # Once per minute max
        'time_limit': 300,      # 5 minute time limit
    },
    'backend.app.tasks.player_tasks.process_player_action': {
        'rate_limit': '1000/m', # Max 1000 player actions per minute
        'time_limit': 10,       # 10 second time limit
    },
}

# Configure logging
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
    return "Celery is working!"


# Error handling
@celery_app.task(bind=True)
def handle_task_failure(self, task_id, error, traceback):
    """Handle task failures."""
    logger.error(f"Task {task_id} failed: {error}")
    logger.error(f"Traceback: {traceback}")
    
    # Could send to monitoring service or alert system
    return f"Task {task_id} failure handled"


# Task success callback
def task_success_handler(sender=None, headers=None, body=None, **kwargs):
    """Handle successful task completion."""
    logger.info(f"Task {sender} completed successfully")


# Task failure callback
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Handle task failures."""
    logger.error(f"Task {task_id} failed: {exception}")
    
    # Could implement retry logic or alerting here
    if hasattr(sender, 'retry'):
        # Retry with exponential backoff
        try:
            sender.retry(countdown=60, max_retries=3)
        except Exception as retry_error:
            logger.error(f"Failed to retry task {task_id}: {retry_error}")


# Connect signal handlers
from celery.signals import task_success, task_failure
task_success.connect(task_success_handler)
task_failure.connect(task_failure_handler)


# Health check task
@celery_app.task
def health_check():
    """Health check task for monitoring."""
    import redis
    from sqlalchemy import create_engine, text
    
    try:
        # Check Redis connection
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        
        # Check database connection
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "redis": "connected",
            "database": "connected",
            "timestamp": str(datetime.utcnow())
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": str(datetime.utcnow())
        }


# Utility function to get Celery app
def get_celery_app():
    """Get the Celery application instance."""
    return celery_app


if __name__ == '__main__':
    celery_app.start()

from datetime import datetime
