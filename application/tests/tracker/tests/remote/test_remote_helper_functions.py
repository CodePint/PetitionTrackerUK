import pytest
from freezegun import freeze_time
from unittest import mock
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests.tracker.tests.remote.conftest import TestRemotePetition
from application.tracker.remote import RemotePetition
import logging

remote_petition_path = "application.tracker.remote"
logger = logging.getLogger(__name__)


class TestRemotePetitionHelperFunctions(TestRemotePetition):

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.configure()

    def test_get_base_url(self):
        assert RemotePetition.get_base_url(archived=False) == self.base_url
        assert RemotePetition.get_base_url(archived=True) == self.base_archive_url

    def test_url_addr(self):
        assert RemotePetition.url_addr(self.id, archived=False) == self.petition_url()

    def test_page_url_template(self, state="open"):
        result = RemotePetition.page_url_template(state, archived=False)
        assert result == self.page_url_template(state)

    def test_find_page_nums(self):
        expected = {"first": None, "self": "1", "next": "2", "prev": None, "last": "100"}
        links = self.make_links(self_num=1, next_num=2, prev_num=None, last_num=100)
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