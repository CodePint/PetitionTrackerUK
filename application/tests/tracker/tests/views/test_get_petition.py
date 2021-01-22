import pytest
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.tracker.tests.views.conftest import TestTrackerViews
from application.tracker.models import Petition, Record
from freezegun import freeze_time
from unittest import mock
from copy import deepcopy
from datetime import timedelta
from datetime import datetime as dt
import os, json, logging, requests

logger = logging.getLogger(__name__)


def configure_test_get_petition(cls, **kwargs):
    cls.initialize_petitions(kwargs["petitions"])
    if kwargs["records"]: cls.create_records(kwargs["records"])

class TestGetPetition(TestTrackerViews):

    time_now = FROZEN_DATETIME
    time_epoch = (FROZEN_DATETIME - timedelta(hours=8))

    @classmethod
    def initialize_petitions(cls, number_of_petitions):
        defaults = dict(signature_count=range(1000, 100_000), signatures_by={"locales": "auto"})
        cls.petition_data = cls.build(generic=number_of_petitions, defaults=defaults)
        cls.petition_managers = cls.manage(cls.petition_data)
        cls.petitions = cls.seed(cls.petition_data)

    @classmethod
    def create_records(cls, number_of_records=None):
        cls.number_of_records = number_of_records
        for i in range(1, number_of_records + 1):
            timestamp = cls.time_epoch + timedelta(hours=i)
            for manager in cls.petition_managers:
                poll = {"records": {"geo": {"save": True}}, "timestamp": timestamp}
                manager.increment(count=range(1, 100), session=cls.session, commit=True, **poll)

        timestamp = cls.time_now - timedelta(minutes=5)
        for manager in cls.petition_managers:
            poll = {"records": {"base": {"save": True}}, "timestamp": timestamp}
            manager.increment(count=range(1, 100), session=cls.session, commit=True, **poll)



@pytest.mark.parametrize(
    "class_session",
    [{"func": configure_test_get_petition, "petitions": 3, "records": 0}],
    indirect=True
)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestGetPetitionData(TestGetPetition):

    @pytest.mark.parametrize("petition_id" ,[(1), (2), (3)])
    def test_returns_200_with_petition_data_if_found(self, petition_id, app):
        response = app.test_client().get(f"/petition/{petition_id}")
        assert self.validate_status(response, 200)
        assert self.validate_petition(response.json["petition"], petition_id)

    @pytest.mark.parametrize("petition_id" , [(5)])
    def test_raises_404_if_petition_not_found(self, petition_id, app):
        response = app.test_client().get(f"/petition/{petition_id}")
        assert self.validate_status(response, 404)



@pytest.mark.parametrize(
    "class_session",
    [{"func": configure_test_get_petition, "petitions": 2, "records": 5}],
    indirect=True
)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestGetPetitionAndSignaturesData(TestGetPetition):

    time_now = FROZEN_DATETIME
    time_epoch = (FROZEN_DATETIME - timedelta(hours=8))

    petition_id = 1
    route = f"/petition/{petition_id}"

    def test_without_timestamp_returns_latest_signatures_data(self, app):
        params = {"signatures": True}
        response = app.test_client().get(self.route, query_string=params)
        expected =  self.petition_managers[0].timeline[self.number_of_records].records.geo
        assert self.validate_status(response, 200)
        data = response.json

        assert self.validate_petition(data["petition"], self.petition_id)
        assert self.validate_nested_record(data["signatures"], expected)

    def test_with_timestamp_returns_closest_signatures_data(self, app):
        time_after_epoch = timedelta(hours=3.5)
        timestamp = self.time_epoch + time_after_epoch
        params = {"signatures": True, "timestamp": dt.strftime(timestamp, "%d-%m-%YT%H:%M:%S")}
        response = app.test_client().get(self.route, query_string=params)
        expected = self.petition_managers[0].timeline[3].records.geo
        assert self.validate_status(response, 200)
        data = response.json

        assert self.validate_petition(data["petition"], self.petition_id)
        assert self.validate_nested_record(response.json["signatures"], expected)

    def test_with_timestamp_and_no_record_found_returns_empty_signatures_data(self, app):
        time_before_epoch = timedelta(hours=1)
        timestamp = self.time_epoch - time_before_epoch
        params = {"signatures": True, "timestamp": dt.strftime(timestamp, "%d-%m-%YT%H:%M:%S")}
        response = app.test_client().get(self.route, query_string=params)
        assert self.validate_status(response, 200)
        data = response.json

        assert self.validate_petition(data["petition"], self.petition_id)
        assert data["signatures"] == {}