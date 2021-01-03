import pytest
from munch import Munch as ObjDict
from freezegun import freeze_time
from application.tests import FROZEN_TIME_STR, FROZEN_DATETIME
from application.tracker.models import Petition
from application.tests.conftest import rkwargs
from application.tests.tracker.tests.models.conftest import TestRecordModel, TestPetitionModel
from application.tests.tracker.factories.petition import PetitionFactory, PetitionFactoryManager
from application.tests.tracker.factories.signatures import SignaturesByFactory
from application.tracker.models import Record, Petition

from unittest import mock
from copy import deepcopy
from random import randrange
from datetime import datetime as dt
from datetime import timedelta
import os, json, logging, random

logger = logging.getLogger(__name__)



def configure_distinct_on(cls, **kwargs):
    cls.initialize_time()
    cls.initialize_managers()
    cls.initialize_records()

@pytest.mark.parametrize("class_session", [{"func": configure_distinct_on}], indirect=True)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestRecordDistinctOn(TestRecordModel):

    petition_ids = {"open": [1,2,3], "closed": 4, "archived": 5}
    petition_configs = [
        {"name": "open", "count": 3, "columns": {"state": "open", "archived": False}},
        {"name": "closed", "count": 1,"columns": {"state": "closed", "archived": False}},
        {"name": "archived", "count": 1, "columns": {"state": "open", "archived": True}},
    ]
    petition_defaults = {
        "signature_count": range(1000, 100_000),
        "signatures_by": {
            "country": {"locales": {"undef": 3, "predef": [{"code": "GB", "range": "auto"}]}},
            "constituency": {"locales": {"undef": 3}},
            "region": {"locales": {"undef": 3}}
        }
    }

    @classmethod
    def initialize_time(cls):
        cls.time_now = FROZEN_DATETIME
        cls.time_epoch = (FROZEN_DATETIME - timedelta(hours=10))
        cls.timestamps = [cls.time_epoch + timedelta(hours=i) for i in range(1, 11)]

    @classmethod
    def initialize_managers(cls):
        starting_id = 0
        cls.managers = {}
        for config in cls.petition_configs:
            columns = dict(**cls.petition_defaults, **config["columns"])
            params = {"generic": config["count"], "starting_id": starting_id}
            petitions = cls.build_petitions(defaults=columns, **params)
            cls.seed_petitions(petitions, cls.session)
            cls.managers[config["name"]] = cls.manage_petitions(petitions)
            starting_id += config["count"]

    @classmethod
    def initialize_records(cls):
        params = {"count": 1000, "commit": True, "session": cls.session}
        for param, petition_managers in cls.managers.items():
            for manager in petition_managers:
                for timestamp in cls.timestamps:
                    records = {"base": {"save": True}, "geo": {"save": True}}
                    manager.increment(records=records, timestamp=timestamp, **params)

    @classmethod
    def make_params(cls, state, archived, geographic, petitions, order_by, timestamp):
        params = {"opts": {"state": state, "archived": archived, "geographic": geographic}}
        params["petitions"] = petitions
        params["order_by"] = order_by
        if timestamp:
            if timestamp.get("lt"):
                timestamp["lt"] = cls.time_now - timedelta(**timestamp["lt"])
            if timestamp.get("gt"):
                timestamp["gt"] = cls.time_epoch + timedelta(**timestamp["gt"])

        params["timestamp"] = timestamp
        return params

    def is_distinct(self, records):
        unique = set(r.petition_id for r in records)
        assert len(unique) == len(records)
        return True

    def validate_query(self, records, petitions, order_by, timestamp, opts):
        ordering = getattr(Record.timestamp, order_by.lower())
        query = Record.query.join(Petition)
        ordering = [Record.petition_id, ordering()]
        filters = []
        filters.append(Petition.archived == opts.get("archived"))
        if opts.get("state"):
            filters.append(Petition.state == Petition.STATE_LOOKUP[opts["state"]])
        if opts["geographic"] is not None:
            filters.append(Record.geographic == opts["geographic"])
        if timestamp.get("lt"):
            filters.append(Record.timestamp < timestamp["lt"])
        if timestamp.get("gt"):
            filters.append(Record.timestamp > timestamp["gt"])

        for r in records:
            if petitions:
                assert r.petition.id in petitions
            query = r.petition.records.filter(*filters)
            expected = query.order_by(*ordering).first()
            assert r.id == expected.id
        return True

    # order_by => DESC returns newest record, ASC returns oldest record
    @pytest.mark.parametrize("state,archived,geographic,petitions,order_by,timestamp",
        [
            ("open", False, False, [1,2,4,5], "DESC", {"gt": {"hours": 100}, "future": True}),
            ("open", False, True, [2,3,4,5], "DESC", {"lt": {"hours": 2}, "gt": {"hours": 2}}),
            ("open", False, False, [2,3,4,5], "DESC", {"lt": {"hours": 2}, "gt": {"hours": 2}}),
            ("open", False, True, [2,3,4,5], "DESC", {"lt": {"hours": 3}}),
            ("closed", False, True, False, "ASC", {"gt":  {"hours": 3}}),
            ("open", True, True, False, "ASC", {}),
        ]
    )
    def test_records_distinct_on(self, state, archived, geographic, petitions, order_by, timestamp):
        params = self.make_params(state, archived, geographic, petitions, order_by, timestamp)
        records = Record.distinct_on(**params)
        if params["timestamp"].get("future"):
            assert not any(records)
            return True
        else:
            assert any(records)

        assert self.is_distinct(records)
        assert self.validate_query(records=records, **params)
