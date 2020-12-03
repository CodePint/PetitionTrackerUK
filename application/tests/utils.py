import logging, subprocess, os
from datetime import datetime

logger = logging.getLogger(__name__)

class Compose():

    filename = "docker-compose.pytest.yml"

    @classmethod
    def up(cls):
        logger.info("starting pytest docker containers")
        subprocess.run(["docker-compose", "-f", cls.filename, "up", "-d"])

    @classmethod
    def down(cls):
        logger.info("removing pytest docker containers")
        subprocess.run(["docker-compose", "down"])

Compose.up()