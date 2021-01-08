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
from application.tracker.exceptions import PetitionsNotFound, RecordsNotFound

from unittest import mock
from copy import deepcopy
from random import randrange
from datetime import datetime as dt
from datetime import timedelta
import os, json, logging, random

logger = logging.getLogger(__name__)



def configure_trend_indexes(cls, **kwargs):
    cls.initialize_petitions(kwargs["total"])
    cls.initialize_managers(kwargs["missing"])
    cls.dummy_poll(cls.petition_managers, cls.poll_increments["before"])
    cls.dummy_poll(cls.managers["found"], cls.poll_increments["distinct"])
    cls.mock_previous_update()
    cls.dummy_poll(cls.petition_managers, cls.poll_increments["after"])
    cls.mock_current_poll()
    cls.set_distinct_growth()
    cls.expected_managers_by_id()

@pytest.mark.parametrize(
    "class_session",
    [{"func": configure_trend_indexes, "missing": 5, "total": 15}],
    indirect=True
)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestPetitionUpdateTrendIndexes(TestPetitionModel):

    time_now = FROZEN_DATETIME
    time_epoch = (FROZEN_DATETIME - timedelta(hours=3))
    poll_increments = {"before": [0, 30, 60, 90], "distinct": [120], "after": [150]}
    distinct_index = 5

    @classmethod
    def initialize_petitions(cls, total):
        defaults = {"state": "open", "signature_count": range(1, 100), "signatures_by": {"locales": 1}}
        cls.initial_data = cls.build(generic=total, defaults=defaults)
        cls.seed(cls.initial_data)

    @classmethod
    def initialize_managers(cls, missing):
        cls.petition_managers = cls.manage(cls.initial_data)
        random.shuffle(cls.petition_managers)
        cls.managers = {}
        cls.managers["missing"] = cls.petition_managers[:missing]
        cls.managers["found"] = cls.petition_managers[missing:]

    @classmethod
    def dummy_poll(cls, managers, increments):
        for i in increments:
            timestamp = cls.time_epoch + timedelta(minutes=i)
            for manager in managers:
                poll = {"records": {"base": {"save": True}}, "timestamp": timestamp}
                manager.increment(count=range(1, 100), session=cls.session, commit=True, **poll)

    @classmethod
    def mock_current_poll(cls):
        signatures = random.sample(range(1, 100), len(cls.petition_managers))
        managers = cls.managers["found"] + cls.managers["missing"]
        for manager, count in zip(managers, signatures):
            poll = {"records": {"base": {"save": True}}, "timestamp": cls.time_now}
            manager.increment(count=count, session=cls.session, commit=True, **poll)

    @classmethod
    def mock_previous_update(cls):
        initial_growth = lambda m: m.timeline[1].records.base.avg_growth_since()
        managers = cls.managers["found"] + cls.managers["missing"]
        managers.sort(key=lambda x: initial_growth(x), reverse=True)
        for index, manager in enumerate(managers):
            growth_rate = initial_growth(manager)
            manager.growth_rate = growth_rate
            manager.petition.growth_rate = growth_rate
            manager.petition.trend_index = index + 1

        cls.session.commit()

    @classmethod
    def set_distinct_growth(cls):
        cls.distinct_records = []
        for manager in cls.managers["found"]:
            manager.distinct_record = manager.timeline[cls.distinct_index].records.base
            manager.growth_rate = manager.distinct_record.avg_growth_since()
            cls.distinct_records.append(manager.distinct_record)

    @classmethod
    def expected_managers_by_id(cls):
        cls.managers["found"].sort(key=lambda x: x.petition_id)
        cls.managers["missing"].sort(key=lambda x: x.petition_id)
        cls.expected_missing_ids = [m.petition_id for m in cls.managers["missing"]]
        cls.expected_found_ids = [m.petition_id for m in cls.managers["found"]]

    @classmethod
    def manage_expectations(cls, handler, missing=False):
        sort_growth = lambda managers: sorted(managers, key=lambda x: x.growth_rate, reverse=True)
        combined_managers = cls.managers["found"] + cls.managers["missing"]
        if handler == "concat":
            indexed_managers = sort_growth(cls.managers["found"]) + sort_growth(cls.managers["missing"])
        elif handler == "reindex":
            managers = cls.managers["found"] if missing else combined_managers
            indexed_managers = sort_growth(managers)
        else:
            return
        for index, manager in enumerate(indexed_managers):
            manager.expected = {"trend_index": index + 1, "growth_rate": manager.growth_rate}

    def validate_updates(self, result, managers):
        for petition, manager in zip(result, managers):
            assert petition.trend_index == manager.expected["trend_index"]
            assert petition.growth_rate == manager.expected["growth_rate"]
        return True

    def delete_missing_petitions(self):
        query = Petition.query.filter(Petition.id.in_(self.expected_missing_ids))
        query.delete(synchronize_session=False)
        self.session.commit()

    def delete_disinct_records(self):
        distinct_ids = [r.id for r in self.distinct_records]
        query = Petition.query.filter(Record.id.in_(distinct_ids))
        query.delete(synchronize_session=False)
        self.session.commit()

    @pytest.mark.parametrize("handler", [("concat"), ("reindex")])
    def test_with_missing(self, handler):
        self.manage_expectations(handler)
        result = Petition.update_trend_indexes(handle_missing=handler)
        result["found"].sort(key=lambda x: x.id)
        result["missing"].sort(key=lambda x: x.id)

        assert self.expected_missing_ids == [p.id for p in result["missing"]]
        assert self.expected_found_ids == [p.id for p in result["found"]]
        assert self.validate_updates(result["found"], self.managers["found"])
        assert self.validate_updates(result["missing"], self.managers["missing"])

    def test_with_missing_and_raise(self, handler=False):
        expected_message = "Petition(s) not found, for trend index update."
        expected_message += f" Missing ids: {self.expected_missing_ids}."
        expected_message += f" Found ids: {self.expected_found_ids}."

        error = None
        with pytest.raises(PetitionsNotFound) as error:
            result = Petition.update_trend_indexes(handle_missing=handler)
        assert str(error.value) == expected_message

    @pytest.mark.parametrize("handler", [("concat"), ("reindex"), (False)])
    def test_without_missing(self, handler):
        self.delete_missing_petitions()
        self.manage_expectations(handler, missing=True)
        result = Petition.update_trend_indexes(handle_missing=handler)
        result["found"].sort(key=lambda x: x.id)

        assert not any(result["missing"])
        assert self.expected_found_ids == [p.id for p in result["found"]]
        assert self.validate_updates(result["found"], self.managers["found"])

    def test_raises_without_found(self, handler=False):
        self.delete_disinct_records()
        expected_message = "Record(s) not found, for growth rate update."
        expected_message += f" Found ids: []."

        error = None
        with pytest.raises(RecordsNotFound) as error:
            result = Petition.update_trend_indexes(handle_missing=handler)
        assert str(error.value) == expected_message
