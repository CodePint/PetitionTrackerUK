import pytest
from munch import Munch as ObjDict
from freezegun import freeze_time
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests.conftest import rkwargs
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.tracker.tests.remote.conftest import (
    TestRemotePetitionRequests,
    TestRemotePetitionFutureRequests
)
from application.tracker.remote import RemotePetition
from urllib.parse import urlparse, parse_qs
from requests import HTTPError
from unittest import mock
from copy import deepcopy
import logging, requests

logger = logging.getLogger(__name__)



@freeze_time(FROZEN_TIME_STR)
class TestRemotePetitionAsyncGet(TestRemotePetitionFutureRequests):

    def configure(self):
        super().configure()
        self.response_json = {"links": {"self": self.base_url}, "data": {}}

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.configure()
        self.patch_future_session()
        self.patch_async_get()

        yield

        for p in self.patches.values(): p.stop()

    def patch_async_get(self):
        import_path =  f"{self.base_import_path}.RemotePetition.async_get"
        self.patches.async_get = mock.patch(import_path, wraps=RemotePetition.async_get)
        self.mocks.async_get = self.patches.async_get.start()

    @pytest.fixture(scope="function")
    def petitions(self, count=10):
        return [ObjDict(id=id, url=RemotePetition.url_addr(id)) for id in range(count)]

    def validate_function(self, call_count):
        assert RemotePetition.async_get.call_count == call_count
        for response in self.results["success"] + self.results["failed"]:
            assert response.petition == response.expected_object["petition"]

        return True

    def test_when_poll_and_none_fail(self, petitions, kwargs={"max_retries": 3, "backoff": 0}):
        self.request_failures = 0
        self.results = RemotePetition.async_get(petitions=petitions, **kwargs)
        assert self.validate_responses(success=10, failed=0)
        assert self.validate_function(call_count=1)

    def test_when_poll_and_some_fail(self, petitions, kwargs={"max_retries": 3, "backoff": 0}):
        self.request_failures = (kwargs["max_retries"] * len(petitions)) + 5
        self.results = RemotePetition.async_get(petitions=petitions, **kwargs)
        assert self.validate_responses(success=5, failed=5)
        assert self.validate_function(call_count=4)

    def test_when_poll_and_all_fail(self, petitions, kwargs={"max_retries": 3, "backoff": 0}):
        self.request_failures = (kwargs["max_retries"] * len(petitions)) + len(petitions)
        self.results = RemotePetition.async_get(petitions=petitions, **kwargs)
        assert self.validate_responses(success=0, failed=10)
        assert self.validate_function(call_count=4)

    def test_when_populate_and_none_fail(self, kwargs={"max_retries": 3, "backoff": 0}):
        petitions = range(0, 10)
        self.request_failures = 0
        self.results = RemotePetition.async_get(petitions, **kwargs)
        assert self.validate_responses(success=10, failed=0)
        assert self.validate_function(call_count=1)

    def test_when_populate_and_some_fail(self, kwargs={"max_retries": 3, "backoff": 0}):
        petitions = range(0, 10)
        self.request_failures = (kwargs["max_retries"] * len(petitions)) + 5
        self.results = RemotePetition.async_get(petitions=petitions, **kwargs)
        assert self.validate_responses(success=5, failed=5)
        assert self.validate_function(call_count=4)

    def test_when_populate_and_all_fail(self, kwargs={"max_retries": 3, "backoff": 0}):
        petitions = range(0, 10)
        self.request_failures =  (kwargs["max_retries"] * len(petitions)) + len(petitions)
        self.results = RemotePetition.async_get(petitions=petitions, **kwargs)
        assert self.validate_responses(success=0, failed=10)
        assert self.validate_function(call_count=4)


@freeze_time(FROZEN_TIME_STR)
class TestRemotePetitionAsyncQuery(TestRemotePetitionFutureRequests):

    def configure(self):
        super().configure()
        self.num_pages = 10
        self.items_per_page = 5
        self.response_links = self.make_links()
        self.response_data = [{}, {}, {}, {}, {}]
        self.response_json = {"links": self.response_links, "data": self.response_data}

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.configure()
        self.patch_future_session()
        self.patch_standard_session()
        self.patch_async_query()

        yield

        for p in self.patches.values(): p.stop()

    def mock_standard_get(self, url, *args, **kwargs):
        get_val = lambda url, key: (parse_qs(urlparse(url).query).get(key) or [None])[0]
        first_num = get_val(url, "page")
        response = requests.Response()
        response.status_code = 200
        links = self.make_links(next_num=int(first_num) + 1, last_num=self.num_pages)
        response.json = MagicMock(return_value={"links": links, "data": self.response_data.copy()})
        return response

    def patch_standard_session(self):
        import_path =  f"{self.base_import_path}.RemotePetition.standard_session"
        self.patches.standard_session = mock.patch(import_path)
        self.mocks.standard_session = self.patches.standard_session.start()
        self.mocks.standard_session.get = MagicMock(wraps=self.mock_standard_get)

    def patch_async_query(self):
        import_path =  f"{self.base_import_path}.RemotePetition.async_query"
        self.patches.async_query = mock.patch(import_path, wraps=RemotePetition.async_query)
        self.mocks.async_query = self.patches.async_query.start()

    def validate_function(self, success, call_count):
        assert RemotePetition.async_query.call_count == call_count
        assert len(self.unpacked_results) == (success * self.items_per_page)
        for response in self.results["success"] + self.results["failed"]:
            assert response.index == response.expected_object["index"]

        return True

    def test_when_none_fail(self, kwargs={"max_retries": 3, "backoff": 0}):
        self.request_failures = 0
        self.results = RemotePetition.async_query(**kwargs)
        self.unpacked_results = RemotePetition.unpack_query(self.results)
        assert self.validate_responses(success=10, failed=0)
        assert self.validate_function(success=10, call_count=1)

    def test_when_some_fail(self, kwargs={"max_retries": 3, "backoff": 0}):
        self.request_failures = (kwargs["max_retries"] * self.num_pages) + 5
        self.results = RemotePetition.async_query(**kwargs)
        self.unpacked_results = RemotePetition.unpack_query(self.results)
        assert self.validate_responses(success=5, failed=5)
        assert self.validate_function(success=5, call_count=4)

    def test_when_all_fail(self, kwargs={"max_retries": 3, "backoff": 0}):
        self.request_failures = (kwargs["max_retries"] * self.num_pages) + self.num_pages
        self.results = RemotePetition.async_query(**kwargs)
        self.unpacked_results = RemotePetition.unpack_query(self.results)
        assert self.validate_responses(success=0, failed=10)
        assert self.validate_function(success=0, call_count=4)

