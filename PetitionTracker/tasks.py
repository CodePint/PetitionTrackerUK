from PetitionTracker import celery

@celery.task()
def celery_file_task(name, content):
    with open(name, "w") as file:
        file.write(content)
