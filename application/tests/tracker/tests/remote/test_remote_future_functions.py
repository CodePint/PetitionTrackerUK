import pytest
from freezegun import freeze_time
from unittest import mock
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests.conftest import rkwargs
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.tracker.tests.remote.conftest import TestRemotePetition
from application.tracker.remote import RemotePetition
import logging, requests

remote_petition_path = "application.tracker.remote"
logger = logging.getLogger(__name__)



class TestRemotePetitionHandleAsyncResponses(TestRemotePetition):

    @pytest.mark.parametrize('futures', [{"success": 10, "failed": 5}], indirect=True)
    def test_handle(self, futures):
        responses = self.futures["success"] + self.futures["failed"]
        result = RemotePetition.handle_async_responses(responses)

        assert (len(result["success"]) + len(result["failed"])) == len(responses)
        assert len(result["success"]) == len(self.futures["success"])
        assert len(result["failed"]) == len(self.futures["failed"])

class TestRemotePetitionEvalAsyncRetry(TestRemotePetition):

    @pytest.fixture(scope="function")
    def configure(self, request):
        self.kwargs = rkwargs(request)
        self.kwargs.update(results=self.futures, retries=0)
        self.attempts = range(self.kwargs.pop("attempts"))

    def validate(self, i):
        assert self.result["retries"] == i + 1
        assert self.result["backoff"] == self.kwargs["backoff"] ** self.result["retries"]
        assert self.result.pop("completed") == self.kwargs["results"]["success"]

    @pytest.mark.parametrize('futures', [{"success": 5, "failed": 20}], indirect=True)
    @pytest.mark.parametrize('configure', [{"backoff": 10, "max_retries": 3, "attempts": 5}], indirect=True)
    def test_will_retry_untill_max_retries_exceeded(self, futures, configure):
        for i in self.attempts:
            self.result = RemotePetition.eval_async_retry(**self.kwargs)
            if i < self.kwargs["max_retries"]:
                self.validate(i)
                self.kwargs = {**self.kwargs, **self.result}
                continue

            assert any(self.kwargs["results"]["failed"])
            assert self.result is False

    @pytest.mark.parametrize('futures', [{"success": 5, "failed": 20}], indirect=True)
    @pytest.mark.parametrize('configure', [{"backoff": 10, "max_retries": 10, "attempts": 5}], indirect=True)
    def test_will_not_retry_without_failures(self, futures, configure):
        for i in self.attempts:
            self.result = RemotePetition.eval_async_retry(**self.kwargs)
            if any(self.kwargs["results"]["failed"]):
                self.validate(i)
                succeeded = [self.kwargs["results"]["failed"].pop(0) for i in range(10)]
                self.kwargs["results"]["success"].append(succeeded)
                self.kwargs = {**self.kwargs, **self.result}
                continue

            assert i < self.kwargs["max_retries"]
            assert self.result is False