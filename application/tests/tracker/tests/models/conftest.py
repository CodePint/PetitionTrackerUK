import pytest
from faker import Faker, providers
from munch import Munch as ObjDict
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.conftest import rkwargs
from application.tracker.models import Petition, Record
from application.tracker.models import (
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency,
)
from application.tracker.models import (
    PetitionSchema,
    RecordSchema,
    PetitionNestedSchema,
    RecordNestedSchema,
    SignaturesBySchema,
    SignaturesByCountrySchema,
    SignaturesByRegionSchema,
    SignaturesByConstituencySchema
)

from application.tests.tracker.factories.signatures import SignaturesByFactory
from application.tests.tracker.factories.petition import PetitionFactory
from application.tests.tracker.factories.query import QueryFactory
from application.tracker.remote import RemotePetition
from unittest import mock
from copy import deepcopy
from datetime import datetime as dt
import os, json, logging, requests

logger = logging.getLogger(__name__)


class TestTrackerModels():

    def configure(self):
        self.patches = ObjDict()
        self.mocks = ObjDict()
        self.base_import_path = "application.tracker.models"

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.configure()
        yield
        for p in self.patches.values(): p.stop()

    @classmethod
    def build(cls, count, starting_id=0, **kwargs):
        kwargs.update(signature_count=range(1000, 100_000), signatures_by=False)
        return PetitionFactory.build(generic=count, starting_id=starting_id, default_values=kwargs)

    @classmethod
    def seed(cls, data, session):
        seeded = []
        for item in data:
            petition = Petition(id=item.data.id, initial_data=item)
            petition.sync(item, dt.now())
            seeded.append(petition)

        session.add_all(seeded)
        session.commit()

        return seeded

    def patch_session_get(self, session):
        function = self.mock_standard_get if session == "standard_session" else self.mock_future_get
        import_path =  f"{self.base_import_path}.Petition.remote.{session}"
        self.patches["session_name"] = mock.patch(import_path)
        self.mocks["session_name"] = self.patches["session_name"].start()
        self.mocks["session_name"].get = MagicMock(wraps=function)

