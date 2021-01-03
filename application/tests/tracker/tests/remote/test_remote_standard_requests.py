import pytest
from freezegun import freeze_time
from unittest.mock import MagicMock, PropertyMock, create_autospec
from unittest import mock
from requests import HTTPError
from application.tests.conftest import rkwargs
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.tracker.tests.remote.conftest import (
    TestRemotePetition,
    TestRemotePetitionRequests,
)
from application.tracker.remote import RemotePetition
import json, logging, requests

remote_petition_path = "application.tracker.remote"
logger = logging.getLogger(__name__)


## synchronous standard requests function tests
@freeze_time(FROZEN_TIME_STR)
class TestRemotePetitionFetch(TestRemotePetitionRequests):

    def configure(self):
        super().configure()
        self.url = self.petition_url()

    @pytest.mark.parametrize(
        'configure_response', [{
            "status_code": 200,
            "response_data": {"links": {}, "data": {}}
        }],
        indirect=True
    )
    def test_when_status_is_200(self, configure_response):
        self.response.url = f"{self.base_url}/{self.id}.json"
        result = RemotePetition.fetch(self.id)
        assert result.data == self.response_data
        assert result.timestamp == FROZEN_DATETIME.isoformat()

    @pytest.mark.parametrize('configure_response', [{"status_code": 404}], indirect=True)
    def test_when_status_is_404_and_wont_raise(self, configure_response):
        self.response.url = f"{self.base_url}/{self.id}.json"
        result = RemotePetition.fetch(self.id, raise_404=False)
        assert result is None

    @pytest.mark.parametrize('configure_response', [{"status_code": 404}], indirect=True)
    def test_when_status_is_404_and_will_raise(self, configure_response):
        expected_msg = f"404 Client Error: Not Found for url: {self.url}"
        error = None
        with pytest.raises(HTTPError) as error:
            result = RemotePetition.fetch(self.id, raise_404=True)
        assert str(error.value) == expected_msg


@freeze_time(FROZEN_TIME_STR)
class TestRemotePetitionGetPageRange(TestRemotePetitionRequests):

    def configure(self):
        super().configure()
        self.template = self.page_url_template("open")
        self.url = self.template % {"page": 1}

    @pytest.mark.parametrize('init_links', [{"next_num": 2, "last_num": 100}], indirect=True)
    @pytest.mark.parametrize('configure_response', [{"status_code": 200}], indirect=True)
    def test_when_status_is_200_and_next_page(self, init_links, configure_response):
        result = RemotePetition.get_page_range(self.template)
        expectation = list(range(1, self.last_num + 1))
        assert result == expectation

    @pytest.mark.parametrize('init_links', [{"next_num": None, "last_num": 1}], indirect=True)
    @pytest.mark.parametrize('configure_response', [{"status_code": 200}], indirect=True)
    def test_status_is_200_and_not_next_page(self, init_links, configure_response):
        result = RemotePetition.get_page_range(self.template)
        expectation = [1]
        assert result == expectation

    @pytest.mark.parametrize('configure_response', [{"status_code": 404}], indirect=True)
    def test_when_status_is_404(self, configure_response):
        expected_msg = f"404 Client Error: Not Found for url: {self.url}"
        error = None
        with pytest.raises(HTTPError) as error:
            result = RemotePetition.get_page_range(self.template)
        assert str(error.value) == expected_msg
