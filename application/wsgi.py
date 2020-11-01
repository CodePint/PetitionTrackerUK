from application import *
import logging

app = create_app()

logger = logging.getLogger(__name__)
logger.info("starting wsgi for petititon tracker app")