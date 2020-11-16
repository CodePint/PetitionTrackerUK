import pytest
from flask import current_app
from freezegun import freeze_time
from datetime import datetime as dt
from datetime import timedelta
import logging

from application.models import Event, EventSchema
from .. import FROZEN_DATETIME, FROZEN_TIME_STR

logger = logging.getLogger(__name__)

@freeze_time(FROZEN_TIME_STR)
class TestDummyEvent():

    @classmethod
    def create_event(cls, session, name, ts=dt.now(), msg="msg"):
        event = Event(name=name, ts=ts, msg=(f"{name}_{msg}"))
        session.add(event)
        session.commit()
        return event

    def test_returns_200_with_the_first_dummy_event(self, app, db, session):
        event_name = "dummy_event"
        expected_event_count = 5
        expected_event = TestDummyEvent.create_event(session, event_name, FROZEN_DATETIME)
        expected_event_dump = {"event": EventSchema().dump(expected_event)}

        for i in range(expected_event_count - 1):
            event_ts = FROZEN_DATETIME - timedelta(minutes=i)
            TestDummyEvent.create_event(session, event_name, dt.now())

        event_dump = app.test_client().get(f"/dummy_event/{event_name}").json
        event_count = Event.query.filter_by(name=event_name).count()

        assert event_count == expected_event_count
        assert event_dump == expected_event_dump

    def test_returns_403_forbidden_if_not_a_dummy_event(self, app, db, session):
        event_name = "real_event"
        event = TestDummyEvent.create_event(session, event_name)
        expected_error_msg = "Only dummy events can be queried from this endpoint"
        response = app.test_client().get(f"/dummy_event/{event_name}")

        assert response.status_code == 403
        assert response.json.get("message") == expected_error_msg


    def test_returns_404_not_found_if_no_matching_events_found(self, app, db, session):
        event_name =  "dummy_event_exists"
        queried_event_name = "dummy_event_not_exists"
        event = TestDummyEvent.create_event(session, event_name)
        expected_error_msg = f"No events found matching name: {queried_event_name}"
        response = app.test_client().get(f"/dummy_event/{queried_event_name}")

        assert response.status_code == 404
        assert response.json.get("message") == expected_error_msg