import pytest
from munch import Munch as ObjDict
from freezegun import freeze_time
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.conftest import rkwargs
from application.tests.tracker.tests.models.conftest import TestPetitionModelRequests
from application.tests.tracker.factories.petition import PetitionFactory
from application.tracker.remote import RemotePetition
from application.tracker.models import Petition, Record
from application.models import Setting
from unittest import mock
from copy import deepcopy
from random import randrange
from datetime import datetime
import os, json, logging, random, requests

logger = logging.getLogger(__name__)



def configure_populate(cls, **kwargs):
    cls.num_petitions = 5
    cls.trend_index = 6
    cls.expected_ids = [1,2,3,4,5]
    defaults = dict(signature_count=range(1000, 100_000), signatures_by={"locales": "auto"})
    cls.remote_data = {p.data.id: p for p in cls.build(generic=10, defaults=defaults)}

@pytest.mark.parametrize("class_session", [{"func": configure_populate}], indirect=True)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestPetitionPopulate(TestPetitionModelRequests):


    def test_populate(self):
        self.populated = Petition.populate(ids=self.expected_ids)
        assert sorted([p.id for p in self.populated]) == self.expected_ids

        expected = {"polled_at": FROZEN_DATETIME, "trend_index": 6}
        for petition in self.populated:
            expected.update(petition=petition, expected=self.remote_data[petition.id])
            assert self.validate_petition(**expected)
