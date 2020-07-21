from flask import current_app
from celery.schedules import crontab

def schedule_tasks():
    return {
    'poll_petitions_task_periodic': {
        'task': 'poll_petitions_task',
        'args': (),
        'schedule': current_app.celery_utils.get_interval('poll_petitions_task'),
        'options': {
            'queue':'periodic_remote_petition'
        }
    },
    'populate_petitions_task_periodic': {
        'task': 'populate_petitions_task',
        'args': ('open',),
        'schedule': current_app.celery_utils.get_interval('populate_petitions_task'),
        'options': {
            'queue':'periodic_remote_petition'
        }
    },
    'test_task_periodic': {
        'task': 'test_task',
        'args': ('test.txt', 'test task fired!'),
        'schedule': current_app.celery_utils.get_interval('test_task'),
        'options': {
            'queue':'default'
        }
    },
}

def startup_tasks():
    return {
    'test_task': {
        'function': current_app.tasks['shared'].test_task,
        'func_args': (
            'test.txt', 'test task fired! (startup)'
        ),
        'async_args': {
            'queue': 'default'
        }
    },

    'populate_petitions_task': {
        'function': current_app.tasks['tracker'].populate_petitions_task,
        'func_args': (
            'open',
        ),
        'async_args': {
            'queue': 'periodic_remote_petition'
        }
    },

    'poll_petitions_task': {
        'function': current_app.tasks['tracker'].poll_petitions_task,
        'func_args': (),
        'async_args': {
            'queue': 'periodic_remote_petition'
        }
    },
}