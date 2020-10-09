from .decorators import if_enabled
from flask import current_app
from celery.schedules import crontab
import sys

class TaskSchedule():

    def __init__(self):
        tasks = {}
        tasks.update(TaskSchedule.poll_total_sigs_task_periodic())
        tasks.update(TaskSchedule.poll_geographic_sigs_task_periodic())
        tasks.update(TaskSchedule.poll_trending_geographic_sigs_task_periodic())
        tasks.update(TaskSchedule.populate_petitions_task_periodic())
        tasks.update(TaskSchedule.update_trending_petitions_pos_task())

        self.tasks = tasks

    @classmethod
    def retry_policy(cls):
        return {
            "max_retries": 3,
            "interval_start": 10,
            "interval_step": 15,
            "interval_max": 60,
        }

    @classmethod
    @if_enabled(task_name="poll_total_sigs_task")
    def poll_total_sigs_task_periodic(cls, task):
        return {
            "poll_total_sigs_task_periodic": {
                "task": "poll_petitions_task",
                "kwargs": {
                    "task_name": task.name,
                    "periodic": True,
                    "where": "all",
                    "signatures_by": False
                },
                "options": {
                    "queue": "tracker",
                    "retry": True,
                    "retry_policy": cls.retry_policy()
                },
                "schedule": task.interval
            }
        }

    @classmethod
    @if_enabled(task_name="poll_geographic_sigs_task")
    def poll_geographic_sigs_task_periodic(cls, task):
        return {
            "poll_geographic_sigs_task_periodic": {
                "task": "poll_petitions_task",
                "kwargs": {
                    "task_name": task.name,
                    "periodic": True,
                    "where": "signatures",
                    "gt": True,
                    "signatures_by": True
                },
                "options": {
                    "queue":"tracker",
                    "retry": True,
                    "retry_policy": cls.retry_policy()
                },
                "schedule": task.interval,
            }
        }

    @classmethod
    @if_enabled(task_name="poll_trending_geographic_sigs_task")
    def poll_trending_geographic_sigs_task_periodic(cls, task):
        return {
            "poll_trending_geographic_sigs_task_periodic": {
                "task": "poll_petitions_task",
                "kwargs": {
                    "task_name": task.name,
                    "periodic": True,
                    "where": "trending",
                    "signatures_by": True
                },
                "options": {
                    "queue":"tracker",
                    "retry": True,
                    "retry_policy": cls.retry_policy()
                },
                "schedule": task.interval,
            }
        }

    @classmethod
    @if_enabled(task_name="populate_petitions_task")
    def populate_petitions_task_periodic(cls, task):
        return {
            "populate_petitions_task_periodic": {
                "task": "populate_petitions_task",
                "kwargs": {
                    "task_name": task.name,
                    "periodic": True,
                    "archived": False,
                    "state": "open",
                },
                "options": {
                    "queue":"tracker",
                    "retry": True,
                    "retry_policy": cls.retry_policy()
                },
                "schedule": task.interval
            }
        }

    @classmethod
    @if_enabled(task_name="update_trending_petitions_pos_task_periodic")
    def update_trending_petitions_pos_task(cls, task):
        return {
            "update_trending_petitions_pos_task_periodic": {
                "task": task.name,
                "kwargs": {
                    "task_name": "update_trending_petitions_pos_task",
                    "periodic": True,
                },
                "options": {
                    "queue":"tracker",
                    "retry": True,
                    "retry_policy": cls.retry_policy()
                },
                "schedule": task.interval
            }
        }

    @classmethod
    @if_enabled(task_name="test_task")
    def test_task_periodic(cls, task):
        return {
            "test_task_periodic": {
                "task": "test_task",
                "kwargs": {
                    "task_name": task.name,
                    "periodic": True,
                    "file": "test.txt",
                    "content": "test task fired! (schedule)",
                },
                "options": {
                    "queue":"default",
                    "retry": False,
                },
                "schedule": task.interval,
            },
        }
