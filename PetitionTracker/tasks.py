from PetitionTracker import celery

@celery.task()
def make_file(name, content):
    with open(name, "w") as file:
        file.write(content)
