from flask import current_app
from celery.schedules import crontab

def retry_policy():
    return {
        'max_retries': 3,
        'interval_start': 10,
        'interval_step': 15,
        'interval_max': 60,
    }

def scheduled_tasks():
    return {
    'poll_total_sigs_task_periodic': {
        'task': 'poll_petitions_task',
        'kwargs': {
            'task_name': 'poll_total_sigs_task',
            'periodic': True,
            'where': 'all',
            'signatures_by': False
        },
        'options': {
            'queue':'tracker',
            'retry': True,
            'retry_policy': retry_policy()
        },
        'schedule': current_app.task.get_interval('poll_total_sigs_task'),
    },
    'poll_geographic_sigs_task_periodic': {
        'task': 'poll_petitions_task',
        'kwargs': {
            'task_name': 'poll_geographic_sigs_task',
            'periodic': True,
            'where': 'signatures_gt',
            'signatures_by': True
        },
        'options': {
            'queue':'tracker',
            'retry': True,
            'retry_policy': retry_policy()
        },
        'schedule': current_app.task.get_interval('poll_geographic_sigs_task'),
    },
    'poll_trending_geographic_sigs_task_periodic': {
        'task': 'poll_petitions_task',
        'kwargs': {
            'task_name': 'poll_trending_geographic_sigs_task',
            'periodic': True,
            'where': 'trending',
            'signatures_by': True
        },
        'options': {
            'queue':'tracker',
            'retry': True,
            'retry_policy': retry_policy()
        },
        'schedule': current_app.task.get_interval('poll_trending_geographic_sigs_task'),
    },
    'populate_petitions_task_periodic': {
        'task': 'populate_petitions_task',
        'kwargs': {
            'task_name': 'populate_petitions_task',
            'periodic': True,
            'archived': False,
            'state': 'open',
        },
        'options': {
            'queue':'tracker',
            'retry': True,
            'retry_policy': retry_policy()
        },
        'schedule': current_app.task.get_interval('populate_petitions_task'),
    },
    'update_trending_petitions_pos_task_periodic': {
        'task': 'update_trending_petitions_pos_task',
        'kwargs': {
            'task_name': 'update_trending_petitions_pos_task',
            'periodic': True,
        },
        'options': {
            'queue':'tracker',
            'retry': True,
            'retry_policy': retry_policy()
        },
        'schedule': current_app.task.get_interval('update_trending_petitions_pos_task'),
    },
    'test_task_periodic': {
        'task': 'test_task',
        'kwargs': {
            'task_name': 'test_task',
            'periodic': True,
            'file': 'test.txt',
            'content': 'test task fired! (schedule)',
        },
        'options': {
            'queue':'default',
            'retry': False,
        },
        'schedule': current_app.task.get_interval('test_task'),
    },
}
