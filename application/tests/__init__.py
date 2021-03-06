import logging, subprocess, datetime

logger = logging.getLogger(__name__)

FROZEN_TIME_LIST_INT = [2020, 1, 1, 12, 0, 0]
FROZEN_DATETIME =  datetime.datetime(*FROZEN_TIME_LIST_INT)
FROZEN_TIME_STR = FROZEN_DATETIME.strftime("%d-%m-%YT%H:%M:%S")

class Compose():

    @classmethod
    def up(cls):
        logger.info("starting pytest docker containers")
        subprocess.run(["docker-compose", "up", "-d"])

    @classmethod
    def down(cls):
        logger.info("removing pytest docker containers")
        subprocess.run(["docker-compose", "down"])
