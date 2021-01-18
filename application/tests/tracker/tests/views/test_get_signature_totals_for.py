import pytest
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.tracker.factories.petition import PetitionFactory, PetitionFactoryManager
from application.tests.tracker.tests.views.conftest import TestTrackerViews
from application.tests.tracker.conftest import uk_locale
from application.tracker.models import Petition, Record, RecordSchema
from freezegun import freeze_time
from unittest import mock
from datetime import timedelta
from datetime import datetime as dt
from copy import deepcopy
import os, json, uuid, random, logging

logger = logging.getLogger(__name__)



def configure_test_get_signature_totals(cls, **kwargs):
    signatures_by = {"country": {"locales": {"predef": [uk_locale()], "undef": 3}}}
    config = dict(signature_count=range(100, 100_000), signatures_by=cls.signatures_by)
    cls.initial_data = PetitionFactory(petition_id=1, **config)
    cls.petition_manager = PetitionFactoryManager(cls.initial_data)
    cls.petition = cls.seed([cls.initial_data], cls.session)[0]
    cls.create_records(cls.petition_manager, increment={"hours": 24}, geo=True)



@pytest.mark.parametrize("class_session", [{"func": configure_test_get_signature_totals}], indirect=True)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestGetSignatureTotals(TestTrackerViews):

    time_since_epoch = timedelta(days=30)
    time_now = FROZEN_DATETIME
    time_epoch = (FROZEN_DATETIME - time_since_epoch)

    petition_id = 1
    route = f"/petition/{petition_id}/signatures"

    signatures_by = {
            "country": {"locales": {"predef": [uk_locale()], "undef": 1}},
            "constituency":  {"locales": {"undef": 1}},
            "region":  {"locales": {"undef": 1}},
        }

    @classmethod
    def validate_latest_data(cls, actual):
        expected = cls.ordered_records().first()
        assert RecordSchema(exclude=["id"]).dump(expected) == actual
        return True

    @classmethod
    def validate_signatures(cls, expected, actual):
        assert RecordSchema(many=True, exclude=["id"]).dump(expected) == actual
        return True

    @pytest.mark.parametrize(
        "timestamp,order", [
            (None, None),
            ({"lt": {"days": 2}}, "DESC"),
            ({"gt": {"days": 4}}, "ASC"),
            ({"lt": {"days": 2}, "gt": {"days": 5}}, "DESC"),
        ]
    )
    def test_get_total_signatures(self, timestamp, order, app):
        params = {}

        if order:
            params["order"] = order
        else:
            order = "DESC"

        order = params.get("order", "DESC")
        if timestamp:
            timestamp = self.get_timestamp_param(**timestamp)
            expected_records = self.get_expected_records(geographic=True, order=order, **timestamp)
            params["timestamp"] = self.strftime_dict(timestamp)
        else:
            expected_records = self.ordered_records(geographic=True, order=order).all()


        response = app.test_client().get(self.route, query_string=self.to_qs(params))
        assert self.validate_status(response, 200)
        data = response.json

        assert self.validate_latest_data(data["meta"]["latest_data"])
        assert self.validate_petition(data["petition"], self.petition_id)
        assert self.validate_signatures(expected_records, data["signatures"])

    def test_petition_not_found_returns_404(self, app, petition_id=999):
        route = f"/petition/{petition_id}/signatures"
        response = app.test_client().get(route)
        assert self.validate_status(response, 404)