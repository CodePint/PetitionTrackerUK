import pytest
from munch import Munch as ObjDict
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.conftest import rkwargs
from application.tests.tracker.tests.models.conftest import TestPetitionModelRequests
from application.tests.tracker.factories.query import QueryFactory
from application.tests.tracker.factories.petition import PetitionFactory
from application.tracker.models import Petition, Record
from unittest import mock
from copy import deepcopy
from datetime import datetime as dt
import os, json, logging, requests

logger = logging.getLogger(__name__)



def configure_discover(cls, **kwargs):
    defaults = {"signature_count": range(1000, 100_000), "signatures_by": False}
    cls.counts = {"page": 5, "seeded": 5, "discovered": 15}
    cls.petition_data = cls.build(generic=cls.counts["seeded"], starting_id=0, defaults=defaults)
    cls.to_be_discovered = cls.build(generic=cls.counts["discovered"], starting_id=5, defaults=defaults)
    cls.populated = cls.seed(data=cls.petition_data, session=cls.session)

@pytest.mark.parametrize("class_session", [{"func": configure_discover}], indirect=True)
@pytest.mark.usefixtures("class_session")
class TestPetitionDiscover(TestPetitionModelRequests):

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.configure()
        self.patch_async_query()
        self.patch_session_get("standard_session")
        self.patch_session_get("future_session")

        yield

        for p in self.patches.values(): p.stop()

    def patch_async_query(self):
        import_path =  f"{self.base_import_path}.Petition.remote.async_query"
        self.patches.async_query = mock.patch(import_path, wraps=Petition.remote.async_query)
        self.mocks.async_query = self.patches.async_query.start()

    def mock_standard_get(self, url):
        return self.query.get(url)

    def mock_future_get(self, url, hooks):
        callback = hooks["response"]
        response = self.query.get(url)
        callback(response=response)
        response.result = MagicMock(return_value=response)
        return response

    def test_unpopulated_petitions_are_discovered(self, app):
        self.query = QueryFactory(imports=self.to_be_discovered, items_per_page=self.counts["page"])
        results = Petition.discover(state="open")
        assert Petition.remote.async_query.call_count == 1
        assert len(results) == self.counts["discovered"]
        assert len(results - {p.data.id for p in self.to_be_discovered}) == 0

    def test_existing_petitions_are_not_discovered(self, app):
        self.query = QueryFactory(imports=self.petition_data, items_per_page=self.counts["page"])
        results = Petition.discover(state="open")
        assert Petition.remote.async_query.call_count == 1
        assert len(results) == 0