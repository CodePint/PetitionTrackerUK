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



def configure_test_get_signatures_by_geography(cls, **kwargs):
    config = dict(signature_count=range(10_000, 100_000), signatures_by={"locales": "auto"})
    cls.initial_data = PetitionFactory(petition_id=1, **config)
    cls.petition_manager = PetitionFactoryManager(cls.initial_data)
    cls.petition = cls.seed([cls.initial_data], cls.session)[0]
    cls.create_records(cls.petition_manager, increment={"hours": 24}, geo=True, base=True)

@pytest.mark.parametrize("class_session",
    [{"func": configure_test_get_signatures_by_geography}],
    indirect=True
)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestGetSignaturesByGeography(TestTrackerViews):

    time_since_epoch = timedelta(days=30)
    time_now = FROZEN_DATETIME
    time_epoch = (FROZEN_DATETIME - time_since_epoch)
    geographies = ["region", "country", "constituency"]

    petition_id = 1
    base_route = f"/petition/{petition_id}/signatures_by/"

    @classmethod
    def validate_signatures(cls, expectation, result, geography):
        strftime = lambda t: dt.strftime(t, "%d-%m-%YT%H:%M:%S")
        schema_opts = {"many": True, "exclude": ["id", "record", "timestamp", geography]}
        signatures_schema = RecordSchema.schema_for(geography)(**schema_opts)
        geo_key = f"signatures_by_{geography}"

        assert len(expectation) == len(result)
        for expected, actual in zip(expectation, result):
            assert strftime(expected.timestamp) == actual["timestamp"]
            assert expected.signatures == actual["total"]
            expected_signatures = expected.signatures_by(geography)
            expected_signatures_dump = signatures_schema.dump(expected_signatures)
            assert expected_signatures_dump == actual[geo_key]

        return True

    @pytest.mark.parametrize(
        "geography,timestamp,order", [
            ("region", None, None),
            ("country", {"lt": {"days": 2}}, "DESC"),
            ("constituency", {"lt": {"days": 2}, "gt": {"days": 5}}, "ASC"),
        ]
    )
    def test_get_by_geographies(self, geography, timestamp, order, app):
        route = self.base_route + geography
        params = {}
        if order:
            params["order"] = order

        order = params.get("order", "DESC")
        expected_latest_record = self.ordered_records().first()
        if timestamp:
            timestamp = self.get_timestamp_param(**timestamp)
            expected_records = self.get_expected_records(geographic=True, order=order, **timestamp)
            params["timestamp"] = self.strftime_dict(timestamp)
        else:
            expected_records = self.ordered_records(geographic=True, order=order).all()

        response = app.test_client().get(route, query_string=self.to_qs(params))
        assert self.validate_status(response, 200)
        data = response.json
        latest_data = data["meta"]["latest_data"]

        assert self.validate_petition(data["petition"], self.petition_id)
        assert self.validate_signatures([expected_latest_record], [latest_data], geography)
        assert self.validate_signatures(expected_records, data["signatures"], geography)


    def test_no_signatures_found_returns_404(self, app, petition_id=999, geography="country"):
        route = f"/petition/{petition_id}/signatures_by/{geography}"
        response = app.test_client().get(route)
        assert self.validate_status(response, 404)

    def test_petition_not_found_returns_404(self, app, petition_id=999, geography="country"):
        route = f"/petition/{petition_id}/signatures_by/{geography}"
        response = app.test_client().get(route)
        assert self.validate_status(response, 404)

    def test_invalid_geography_returns_400(self, app, geography="invalid"):
        route = self.base_route + geography
        response = app.test_client().get(route)
        assert self.validate_status(response, 400)