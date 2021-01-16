from flask import current_app
from freezegun import freeze_time
from datetime import datetime as dt
import datetime, pytest, logging, json
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR

logger = logging.getLogger(__name__)

@freeze_time(FROZEN_TIME_STR)
class TestPing():

    def test_returns_200_success_with_time_and_sender(self, app):
        params = {"sender": "pytest"}
        expectation = {**params, "response": "SUCCESS", "time": FROZEN_TIME_STR}
        response = app.test_client().get("/ping", query_string=params)
        result = json.loads(response.data)

        assert result == expectation


    def test_returns_200_success_with_time_and_without_sender(self, app):
        expectation = {"sender": "N/A", "response": "SUCCESS", "time": FROZEN_TIME_STR}
        response = app.test_client().get("/ping")
        result = json.loads(response.data)

        assert result == expectation

