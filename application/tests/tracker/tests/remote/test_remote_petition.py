import pytest
import requests
from requests import HTTPError
from faker import Faker, providers
from freezegun import freeze_time
from munch import Munch as ObjDict

from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import create_autospec
from datetime import timedelta
from datetime import datetime as dt
from random import randint, randrange
from contextlib import contextmanager
from copy import deepcopy
import os, json, logging, random

from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.conftest import get_kwargs
from application.tests.tracker.tests.remote.conftest import (
    make_links
)
from application.tracker.remote import RemotePetition
from application.tracker.remote import SessionMaker, TimeoutHTTPAdapter

remote_petition_path = "application.tracker.remote"
logger = logging.getLogger(__name__)

class TestRemotePetition():

    def configure(self):
        self.import_path = remote_petition_path

        self.id = 9999
        self.base_url = "https://petition.parliament.uk/petitions"
        self.base_archive_url = "https://petition.parliament.uk/archived/petitions"
        self.url = f"{self.base_url}/{self.id}.json"
        self.query_states = [
            "rejected",
            "closed",
            "open",
            "debated",
            "not_debated",
            "awaiting_response",
            "with_response",
            "awaiting_debate",
            "all"
        ]



class TestUnitRemotePetition(TestRemotePetition):

    def test_get_base_url(self):
        assert RemotePetition.get_base_url(archived=False) == self.base_url
        assert RemotePetition.get_base_url(archived=True) == self.base_archive_url

    def test_url_addr(self, id=999):
        assert RemotePetition.url_addr(id, archived=False) == self.base_url + f"/{id}.json"

    def test_page_url_template(self, state="open"):
        result = RemotePetition.page_url_template(state, archived=False)
        assert result == self.base_url + ".json?" + f"page=%(page)s&state={state}"

    def test_find_page_nums(self):
        expected = {"first": None, "self": "1", "next": "2", "prev": None, "last": "100"}
        links = make_links(self_num=1, next_num=2, prev_num=None, last_num=100)
        assert RemotePetition.find_page_nums(links) == expected

    def test_validate_state(self):
        invalid_state = "unknown"
        valid_states = self.query_states
        error_message = f"Invalid state param: '{invalid_state}', valid: {valid_states}"

        for state in valid_states:
            RemotePetition.validate_state(state)

        with pytest.raises(ValueError) as e:
            RemotePetition.validate_state(invalid_state)

        assert str(e.value) == error_message



@freeze_time(FROZEN_TIME_STR)
class TestUnitFetchRemotePetition(TestRemotePetition):

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.configure()
        self.patches = ObjDict()
        self.mocks = ObjDict()
        self.patch_standard_session()

        yield

        for p in self.patches.values(): p.stop()

    @pytest.fixture(scope="function")
    def configure_response(self, request):
        self.response.status_code  = get_kwargs(request).get("status_code")
        if self.response.status_code  == 200:
            self.response.json = MagicMock(return_value=MagicMock(success=True))
        elif self.response.status_code  == 404:
            self.response.reason = "Not Found"

    def patch_standard_session(self):
        import_path = f"{self.import_path}.RemotePetition.standard_session"
        self.response = requests.Response()
        self.response.url = self.url
        self.patches.session = mock.patch(import_path)
        self.mocks.session = self.patches.session.start()
        self.mocks.session.get = create_autospec(requests.get, return_value=self.response)

    @pytest.mark.parametrize('configure_response', [{"status_code": 200}], indirect=True)
    def test_when_response_200(self, configure_response):
        result = RemotePetition.fetch(self.id)
        assert result.data.success is True
        assert result.timestamp == FROZEN_DATETIME.isoformat()

    @pytest.mark.parametrize('configure_response', [{"status_code": 404}], indirect=True)
    def test_when_response_404_and_wont_raise(self, configure_response):
        result = RemotePetition.fetch(self.id, raise_404=False)
        assert result is None

    @pytest.mark.parametrize('configure_response', [{"status_code": 404}], indirect=True)
    def test_when_response_404_and_will_raise(self, configure_response):
        expected_msg = f"404 Client Error: Not Found for url: {self.url}"
        with pytest.raises(HTTPError) as e:
            result = RemotePetition.fetch(self.id, raise_404=True)

        assert str(e.value) == expected_msg
