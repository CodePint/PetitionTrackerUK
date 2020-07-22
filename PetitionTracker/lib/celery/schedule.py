from flask import current_app
from celery.schedules import crontab

def schedule_tasks():
    return {
    'poll_petitions_task_periodic': {
        'task': 'poll_petitions_task',
        'kwargs': {
            'task_name': 'poll_petitions_task',
            'periodic': True,
        },
        'options': {
            'queue':'periodic_remote_petition',
            'retry': True,
        },
        'schedule': current_app.celery_utils.get_interval('poll_petitions_task'),
    },
    'populate_petitions_task_periodic': {
        'task': 'populate_petitions_task',
        'kwargs': {
            'task_name': 'populate_petitions_task',
            'periodic': True,
            'state': 'open',
        },
        'options': {
            'queue':'periodic_remote_petition',
            'retry': True,
        },
        'schedule': current_app.celery_utils.get_interval('populate_petitions_task'),
    },
    'test_task_periodic': {
        'task': 'test_task',
        'kwargs': {
            'task_name': 'test_task',
            'periodic': True,
            'file': 'test.txt',
            'content': 'test task fired! (startup)',
        },
        'options': {
            'queue':'default',
            'retry': True,
        },
        'schedule': current_app.celery_utils.get_interval('test_task'),
    },
}

def startup_tasks():
    return {
    'test_task': {
        'function': current_app.tasks['shared'].test_task,
        'func_kwargs': {
            'task_name': 'test_task',
            'periodic': True,
            'file': 'test.txt',
            'content': 'test task fired! (startup)',
        },
        'async_kwargs': {
            'queue': 'default',
            'retry': True,
        }
    },

    'populate_petitions_task': {
        'function': current_app.tasks['tracker'].populate_petitions_task,
        'func_kwargs': {
            'task_name': 'populate_petitions_task',
            'periodic': True,
            'state': 'open',
        },
        'async_kwargs': {
            'queue': 'periodic_remote_petition',
            'retry': True,
        }
    },

    'poll_petitions_task': {
        'function': current_app.tasks['tracker'].poll_petitions_task,
        'func_kwargs': {
            'task_name': 'poll_petitions_task',
            'periodic': True,
        },
        'async_kwargs': {
            'queue': 'periodic_remote_petition',
            'retry': True,
        }
    },
}