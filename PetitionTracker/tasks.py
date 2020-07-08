from PetitionTracker import celery

@celery.task()
def test_task(name, content):
    with open(name, "w") as file:
        file.write(content)