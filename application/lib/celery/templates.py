from flask import current_app
from celery.schedules import crontab

def template_tasks():
    return {
    'poll_total_sigs_task': {
        'function': current_app.tasks['tracker'].poll_petitions_task,
        'startup': True,
        'func_kwargs': {
            'task_name': 'poll_total_sigs_task',
            'where': 'all',
            'signatures_by': False
        },
        'async_kwargs': {
            'queue': 'tracker',
        }
    },

    'poll_geographic_sigs_task': {
        'function': current_app.tasks['tracker'].poll_petitions_task,
        'startup': True,
        'func_kwargs': {
            'task_name': 'poll_geographic_sigs_task',
            'where': 'signatures_gt',
            'signatures_by': True
        },
        'async_kwargs': {
            'queue':'tracker',
        }
    },
    'poll_trending_geographic_sigs_task': {
        'function': current_app.tasks['tracker'].poll_petitions_task,
        'startup': False,
        'func_kwargs': {
            'task_name': 'poll_trending_task',
            'periodic': True,
            'where': 'trending',
            'signatures_by': True
        },
        'async_kwargs': {
            'queue':'tracker',
        }
    },
    'populate_petitions_task': {
        'function': current_app.tasks['tracker'].populate_petitions_task,
        'startup': True,
        'func_kwargs': {
            'task_name': 'populate_petitions_task'
        },
        'async_kwargs': {
            'queue': 'tracker',
        }
    },
    'update_trending_petitions_pos_task': {
        'function': current_app.tasks['tracker'].update_trending_petitions_pos_task,
        'startup': True,
        'func_kwargs': {
            'task_name': 'update_trending_petitions_pos_task'
        },
        'async_kwargs': {
            'queue': 'tracker',
        }
    },
    'test_task': {
        'function': current_app.tasks['shared'].test_task,
        'func_kwargs': {
            'task_name': 'test_task',
            'file': 'test.txt',
            'content': 'test task fired! (template)'
        },
        'async_kwargs': {
            'queue': 'default',
        }
    },
}
