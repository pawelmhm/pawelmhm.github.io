from datetime import timedelta

CELERYBEAT_SCHEDULE = {
    "poll_SO": {
        "task": "stack_scrap.questions",
        "schedule": timedelta(seconds=30),
        "args": []
    }
}
