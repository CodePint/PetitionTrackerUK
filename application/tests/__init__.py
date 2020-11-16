import logging, subprocess, os

logger = logging.getLogger(__name__)

class Compose():

    @classmethod
    def up(cls):
        logger.info("starting pytest docker containers")
        subprocess.run(["docker-compose", "up", "-d"])

    @classmethod
    def down(cls):
        logger.info("removing pytest docker containers")
        subprocess.run(["docker-compose", "down"])

Compose.up()