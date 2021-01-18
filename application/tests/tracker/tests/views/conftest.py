import pytest
from faker import Faker, providers
from freezegun import freeze_time
from munch import Munch as ObjDict
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from freezegun.api import FakeDate, FakeDatetime

from application.tests.conftest import rkwargs
from application.tracker.models import Petition, Record
from application.tracker.models import (
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency,
)
from application.tracker.models import (
    PetitionSchema,
    RecordSchema,
    PetitionNestedSchema,
    RecordNestedSchema,
    SignaturesBySchema,
    SignaturesByCountrySchema,
    SignaturesByRegionSchema,
    SignaturesByConstituencySchema
)
from application.tests.tracker.conftest import (
    iso_if_dt,
    geography_names,
    get_code_key
)

from application.tests.tracker.factories.petition import (
    PetitionFactory,
    PetitionFactoryManager
)
from application.tests.tracker.factories.signatures import SignaturesByFactory
from application.tests.tracker.factories.query import QueryFactory
from application.tracker.remote import RemotePetition
from unittest import mock
from copy import deepcopy
from datetime import timedelta
from datetime import datetime as dt
import os, json, logging, requests, datetime

class TestTrackerViews():

    def configure(self):
        self.patches = ObjDict()
        self.mocks = ObjDict()
        self.base_import_path = "application.tracker.models"

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.configure()
        yield
        for p in self.patches.values(): p.stop()

    @classmethod
    def to_qs(cls, params):
        json_dump = lambda v: json.dumps(v) if type(v) is not str else v
        return {k: json_dump(v) for k, v in params.items()}

    @classmethod
    def strftime_dict(cls, d):
        return {k: dt.strftime(v, "%d-%m-%YT%H:%M:%S") for k, v in d.items()}

    @classmethod
    def build(cls, generic=0, custom=None, starting_id=0, defaults=None):
        return PetitionFactory.build(generic, custom, starting_id, (defaults or {}))

    @classmethod
    def manage(cls, petitions):
        return [PetitionFactoryManager(p) for p in petitions]

    @classmethod
    def seed(cls, data, session=None, **attributes):
        session = session or cls.session
        trend_index = len(data) + 1
        seeded = []
        for item in data:
            serialized = item.as_dict
            petition = Petition(id=item.data.id, initial_data=serialized)
            petition.trend_index = trend_index
            petition.sync(serialized, dt.now())
            seeded.append(petition)

        session.add_all(seeded)
        session.commit()
        return seeded

    @classmethod
    def create_records(cls, manager, increment, base=False, geo=True, **kwargs):
        current_time = kwargs.get("current_time", cls.time_epoch)
        session = kwargs.get("session", cls.session)
        increment = timedelta(**increment)
        while current_time <= cls.time_now:
            poll = {"records": {"geo": {"save": geo}, "base": {"save": base}}}
            poll["timestamp"] = current_time
            manager.increment(count=range(100, 1000), session=session, commit=True, **poll)
            current_time += increment

    @classmethod
    def get_timestamp_param(cls, lt=None, gt=None):
        timestamp = {}
        if lt:
            timestamp["lt"] = cls.time_now - timedelta(**lt)
        if gt:
            timestamp["gt"] = cls.time_now - timedelta(**gt)
        return timestamp

    @classmethod
    def get_expected_records(cls, lt=None, gt=None, geographic=None, order="DESC"):
        filters = []
        if lt:
            filters.append(Record.timestamp < lt)
        if gt:
            filters.append(Record.timestamp > gt)

        query = cls.petition.records.filter(*filters)
        if geographic is not None:
            query = query.filter_by(geographic=geographic)

        return cls.order_record_query(query, order).all()

    @classmethod
    def ordered_records(cls, geographic=None, order="DESC"):
        query = cls.petition.records
        if geographic is not None:
                query = query.filter_by(geographic=geographic)
        return cls.order_record_query(query, order)

    @classmethod
    def order_record_query(cls, query, order):
        if order == "DESC":
            return query.order_by(Record.timestamp.desc())
        elif order == "ASC":
            return query.order_by(Record.timestamp.asc())
        else:
            raise ValueError("invalid order value")

    @classmethod
    def validate_status(cls, response, code, msg=None):
        assert response.status_code == code
        return True

    @classmethod
    def validate_petition(cls, data, petition_id):
        petition = Petition.query.get(petition_id)
        assert PetitionSchema().dump(petition) == data
        return True

    @classmethod
    def validate_nested_record(cls, data, record):
        record_schema = RecordNestedSchema(exclude=["id", "petition"])
        assert record_schema.dump(record) == data
        return True