import pytest
from faker import Faker, providers
from freezegun import freeze_time
from munch import Munch as ObjDict
from unittest import mock
from unittest.mock import MagicMock
from datetime import timedelta
from datetime import datetime as dt
from random import randint, randrange
from contextlib import contextmanager
from copy import deepcopy
import os, json, logging, random

from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.conftest import get_kwargs
from application.tests.tracker.conftest import (
    fetch_locales_for,
    rand_percent_locales,
    geography_names,
    geography_keys
)
from application.tests.tracker.factories.query import QueryFactory
from application.tests.tracker.factories.petition import PetitionFactory

query_factory_path = "application.tests.tracker.factories.query"
petition_factory_path = "application.tests.tracker.factories.petition"

logger = logging.getLogger(__name__)


# To Do: create assertions
# Simple manual tests show code is solid
class TestQueryFactory():

    def test_load_query(self):
        custom_petitions = [{"signature_count": 110_000, "petition_id": 999, "signatures_by": "auto", "state": "open"}]
        default_values = {"state": "open", "signature_count": range(500, 100_000)}
        petition_kwargs = {"generic": 243, "custom": custom_petitions, "default_values": default_values}
        petitions = PetitionFactory.build(**petition_kwargs)

        self.query = QueryFactory(imports=petitions)
        self.query.get(index=0)

    def test_init_query(self):
        num_pages = 3
        self.query = QueryFactory(num_pages=3)
        self.query.get(index=0)


