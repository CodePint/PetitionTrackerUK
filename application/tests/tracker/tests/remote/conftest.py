import pytest
from munch import Munch as ObjDict
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tracker.remote import RemotePetition
from application.tests.conftest import rkwargs
from unittest import mock
from copy import deepcopy
from datetime import datetime as dt
import os, json, logging, requests

logger = logging.getLogger(__name__)


class TestRemotePetition():

    def configure(self):
        self.patches = ObjDict()
        self.mocks = ObjDict()
        self.id = 9999
        self.base_import_path = "application.tracker.remote"
        self.base_url = "https://petition.parliament.uk/petitions"
        self.base_archive_url = "https://petition.parliament.uk/archived/petitions"
        self.query_states = RemotePetition.query_states

    def page_url_template(self, state):
        return self.base_url + ".json?" + f"page=%(page)s&state={state}"

    def petition_url(self):
        return self.base_url + f"/{self.id}.json"

    @pytest.fixture(scope="function")
    def init_links(self, request):
        kwargs = rkwargs(request)
        self.next_num = kwargs.get("next_num")
        self.last_num = kwargs.get("last_num")
        self.links = self.make_links(next_num=self.next_num, last_num=self.last_num)
        self.response_data = {"links": self.links, "data": [{}, {}, {}, {}, {}]}

    def make_links(self, self_num=False, next_num=False, prev_num=False, last_num=False, state="open"):
        template = "https://petition.parliament.uk/petitions.json?page={}&state="
        make_template = lambda num: template.format(num) + state if num else None
        return {
            "first": "https://petition.parliament.uk/petitions.json?state=open",
            "self": make_template(self_num),
            "last": make_template(last_num),
            "next": make_template(next_num),
            "prev": make_template(prev_num)
        }

    @pytest.fixture(scope="function")
    def futures(self, request):
        kwargs = rkwargs(request)
        make_mock = lambda s: MagicMock(result=MagicMock(return_value=MagicMock(success=s)))
        success = [make_mock(True) for f in range(kwargs.get("success", 0))]
        failed = [make_mock(False) for f in range(kwargs.get("failed", 0))]
        self.futures = {"success": success, "failed": failed}



class TestRemotePetitionRequests(TestRemotePetition):

    def configure(self):
        super().configure()

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.configure()
        self.patches = ObjDict()
        self.mocks = ObjDict()
        self.patch_standard_session()

        yield

        for p in self.patches.values(): p.stop()

    def patch_standard_session(self):
        import_path = f"{self.base_import_path}.RemotePetition.standard_session"
        self.response = requests.Response()
        self.response.url = self.url
        self.patches.standard_session = mock.patch(import_path)
        self.mocks.standard_session = self.patches.standard_session.start()
        self.mocks.standard_session.get = create_autospec(requests.get, return_value=self.response)

    @pytest.fixture(scope="function")
    def configure_response(self, request):
        kwargs = rkwargs(request)
        self.response.url = kwargs.get("url") or self.url
        self.response.status_code  = kwargs.get("status_code")
        if self.response.status_code  == 200:
            self.response_data = kwargs.get("response_data") or getattr(self, "response_data", None)
            self.response.json = MagicMock(return_value=self.response_data)
        elif self.response.status_code  == 404:
            self.response.reason = "Not Found"


class TestRemotePetitionFutureRequests(TestRemotePetition):

    base_import_path = "application.tracker.remote"

    def patch_future_session(self):
        import_path = f"{self.base_import_path}.RemotePetition.future_session"
        self.patches.future_session = mock.patch(import_path)
        self.mocks.future_session = self.patches.future_session.start()
        self.mocks.future_session.get = MagicMock(wraps=self.mock_future_get)

    def mock_future_get(self, *args, **kwargs):
        callback = kwargs["hooks"]["response"]
        response = requests.Response()
        response.closure_args = [c.cell_contents for c in kwargs["hooks"]["response"].__closure__]
        response.expected_object = response.closure_args[1]
        response.json = MagicMock(return_value=deepcopy(self.response_json))
        response.url = kwargs["url"]
        if self.request_failures:
            self.request_failures -= 1
            response.status_code = 500
        else:
            response.status_code = 200
        callback(response=response)
        response.result = MagicMock(return_value=response)
        return response

    def validate_responses(self, success, failed):
        assert len(self.results["success"]) == success
        assert len(self.results["failed"]) == failed
        for response in self.results["success"]:
            assert response.timestamp == FROZEN_DATETIME.isoformat()
            assert response.json.call_count == 1
        for response in self.results["failed"]:
            assert response.json.call_count == 0

        return True