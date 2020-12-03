import pytest
import os, json, logging
from datetime import timedelta
from datetime import datetime as dt

from application.tests.tracker.factories.petition import PetitionFactory
from application.tests.tracker.factories.signatures import SignaturesByFactory

logger = logging.getLogger(__name__)


class TestRemoteFetch():

    def test_fetch_petition_successfully(self, app, db, session):
        pass
        # logger.info("test fetching petition")
        # petition_kwargs = {}
        # petition_kwargs["petition_id"] = 999
        # petition_kwargs["signature_count"] = range(1000, 100_000)

        # signatures_kwargs = {}

        # petition = RemotePetitionFactory(**petition_kwargs)

