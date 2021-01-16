import pytest
from munch import Munch as ObjDict
from freezegun import freeze_time
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.conftest import rkwargs
from application.tests.tracker.tests.models.conftest import TestPetitionModelRequests
from application.tests.tracker.factories.petition import PetitionFactory, PetitionFactoryManager
from application.tracker.remote import RemotePetition
from application.tracker.models import Petition, Record
from application.models import Setting
from unittest import mock
from copy import deepcopy
from random import randrange
from datetime import datetime as dt
import os, json, logging, random, requests

logger = logging.getLogger(__name__)



@freeze_time(FROZEN_TIME_STR)
class TestPetitionPoll(TestPetitionModelRequests):

    signatures_by_kwargs = {
        "country": {"locales": {"undef": 5}},
        "constituency": {"locales": {"undef": 10}},
        "region": {"locales": {"undef": 1}}
    }

    polled_at = FROZEN_DATETIME

    @classmethod
    def configure_poll(cls, session):
        cls.initialize_data()
        cls.increment_data()
        cls.seed_data = cls.seed(data=cls.initial_petitions, session=session)
        cls.trend_index = len(cls.seed_data) + 1

    @classmethod
    def initialize_data(cls):
        defaults = dict(signature_count=range(1000, 100_000), signatures_by={"locales": "auto"})
        cls.initial_petitions = cls.build(generic=5, defaults=defaults)

    @classmethod
    def increment_data(cls):
        cls.petition_managers = {}
        for petition in cls.initial_petitions:
            manager = PetitionFactoryManager(petition)
            for i in range(3):
                count = range(1000, 10_000)
                signatures_by = cls.signatures_by_kwargs.copy()
                manager.increment(count=count, signatures_by=signatures_by)

            cls.petition_managers[manager.petition_id] = manager

    def mock_future_get(self, url, hooks):
        callback = hooks["response"]
        response = requests.Response()
        response.url = url
        response.status_code = 200
        petition_manager = self.petition_managers[int(self.id_from_url(url))]
        petition_data = petition_manager.current.petition.as_dict
        response.json = MagicMock(return_value=petition_data)
        response.result = MagicMock(return_value=response)
        callback(response=response)

        return response

    def test_base_poll(self, session):
        self.configure_poll(session)
        for poll_index in range(3):
            for manager in self.petition_managers.values():
                manager.current_index = poll_index

        result = Petition.poll(geographic=False)

        for record in result:
            manager = self.petition_managers[record.petition_id]
            expected_petition = manager.current.petition
            initial_data = manager.timeline[0].petition.as_dict
            assert self.validate_petition(
                petition=record.petition,
                expected=expected_petition,
                polled_at=FROZEN_DATETIME,
                initial_data=initial_data,
                trend_index=self.trend_index
            )
            assert self.validate_base_record(
                record=record,
                signature_count=expected_petition.signature_count
            )

    def test_geo_poll(self, session):
        self.configure_poll(session)
        for poll_index in range(3):
            for manager in self.petition_managers.values():
                manager.current_index = poll_index

            result = Petition.poll(geographic=True)

            for record in result:
                manager = self.petition_managers[record.petition_id]
                expected_petition = manager.current.petition
                initial_data = manager.timeline[0].petition.as_dict
                assert self.validate_petition(
                    petition=record.petition,
                    expected=expected_petition,
                    polled_at=FROZEN_DATETIME,
                    initial_data=initial_data,
                    trend_index=self.trend_index
                )
                assert self.validate_geo_record(
                    record=record,
                    expected=expected_petition.signatures_by,
                    signature_count=expected_petition.signature_count
                )

