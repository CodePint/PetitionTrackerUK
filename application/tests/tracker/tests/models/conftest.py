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

from application.tests.tracker.factories.signatures import SignaturesByFactory
from application.tests.tracker.factories.petition import PetitionFactory, PetitionFactoryManager
from application.tests.tracker.factories.query import QueryFactory
from application.tracker.remote import RemotePetition
from unittest import mock
from copy import deepcopy
from datetime import datetime as dt
import os, json, logging, requests, datetime

logger = logging.getLogger(__name__)


class TestPetitionModel():

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
    def manage(cls, petitions):
        return [PetitionFactoryManager(p) for p in petitions]

    @classmethod
    def query_ids(cls, ids):
        return Petition.query.filter(Petition.id.in_(ids))

    @classmethod
    def id_from_url(cls, url):
        return url.split('/petitions/')[1].split('.json')[0]

    @classmethod
    def sorted_ids(cls, objects):
        return sorted([o.id for o in objects])

    @classmethod
    def build(cls, generic=0, custom=None, starting_id=0, defaults=None):
        return PetitionFactory.build(generic, custom, starting_id, (defaults or {}))

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
    def update_petitions(cls, petitions, **attributes):
        call_attrs = lambda: {k: v() if callable(v) else v for k, v in attributes.items()}
        petitions = [p.update(**call_attrs(attributes)) for p in petitions]
        cls.db.session.commit()
        return petitions

    @classmethod
    def validate_petition(cls, petition, expected, polled_at, trend_index=None, initial_data=None, growth_rate=0):
        assert cls.validate_properties(petition, expected, polled_at, trend_index, initial_data, growth_rate)
        assert cls.validate_attributes(petition, expected)
        assert cls.validate_datetimes(petition, expected)
        return True

    @classmethod
    def validate_base_record(cls, record, signature_count):
        assert record.signatures == signature_count
        for geo in geography_names():
            assert not any(record.signatures_by(geo))
        return True

    @classmethod
    def validate_geo_record(cls, record, expected, signature_count):
        assert record.signatures == signature_count
        config = cls.setup_record_validation(record, expected)
        for geo, conf in config.items():
            code_key = get_code_key(geo)
            assert len(conf["saved"]) == len(conf["remote"])
            for saved, remote in zip(conf["saved"], conf["remote"]):
                assert getattr(saved, code_key) == remote[code_key]

        return True

    @classmethod
    def setup_record_validation(cls, record, expected):
        config = {}
        for geo in geography_names():
            code_key = get_code_key(geo)
            saved = sorted(record.signatures_by(geo), key=lambda x: getattr(x, code_key).code)
            remote = sorted(expected[f"signatures_by_{geo}"], key=lambda x: x[code_key])
            config[geo] = {"saved": saved, "remote": remote}
        return config

    @classmethod
    def validate_properties(cls, petition, expected, polled_at, trend_index, initial_data, growth_rate):
        assert petition.id == expected.data.id
        assert petition.polled_at == polled_at
        assert petition.trend_index == trend_index
        assert petition.growth_rate == growth_rate
        assert petition.archived == expected.archived
        assert petition.latest_data == expected.as_dict
        assert petition.initial_data == initial_data or expected.as_dict
        assert isinstance(petition.db_created_at, (FakeDatetime, datetime.datetime))
        assert isinstance(petition.db_updated_at, (FakeDatetime, datetime.datetime))
        return True

    @classmethod
    def validate_attributes(cls, petition, expected):
        assert petition.url == expected.links.self
        assert petition.state.value == expected.data.attributes.state
        assert petition.action == expected.data.attributes.action
        assert petition.signatures == expected.data.attributes.signature_count
        assert petition.background == expected.data.attributes.background
        assert petition.creator_name == expected.data.attributes.creator_name
        assert petition.additional_details == expected.data.attributes.additional_details
        return True

    @classmethod
    def validate_datetimes(cls, petition, expected):
        assert petition.pt_created_at == expected.data.attributes.created_at
        assert petition.pt_updated_at == expected.data.attributes.updated_at
        assert petition.pt_rejected_at == expected.data.attributes.rejected_at
        assert petition.moderation_threshold_reached_at == expected.data.attributes.moderation_threshold_reached_at
        assert petition.response_threshold_reached_at == expected.data.attributes.response_threshold_reached_at
        assert petition.debate_threshold_reached_at == expected.data.attributes.debate_threshold_reached_at
        assert petition.government_response_at == expected.data.attributes.government_response_at
        assert petition.scheduled_debate_date == expected.data.attributes.scheduled_debate_date
        assert petition.debate_outcome_at == expected.data.attributes.debate_outcome_at
        return True

    def patch_session_get(self, session):
        function = self.mock_standard_get if session == "standard_session" else self.mock_future_get
        import_path =  f"{self.base_import_path}.Petition.remote.{session}"
        self.patches["session_name"] = mock.patch(import_path)
        self.mocks["session_name"] = self.patches["session_name"].start()
        self.mocks["session_name"].get = MagicMock(wraps=function)



class TestRecordModel():
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
    def build_petitions(cls, generic=0, custom=None, starting_id=0, defaults=None):
        return PetitionFactory.build(generic, custom, starting_id, (defaults or {}))

    @classmethod
    def manage_petitions(cls, petitions):
        return [PetitionFactoryManager(p) for p in petitions]

    @classmethod
    def seed_petitions(cls, data, session):
        return TestPetitionModel.seed(data=data, session=session)



class TestPetitionModelRequests(TestPetitionModel):

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.configure()
        self.patch_future_session()
        self.patch_async_get()

        yield

        for p in self.patches.values(): p.stop()

    def patch_async_get(self):
        import_path =  f"{self.base_import_path}.RemotePetition.async_get"
        self.patches.async_get = mock.patch(import_path, wraps=RemotePetition.async_get)
        self.mocks.async_get = self.patches.async_get.start()

    def mock_future_get(self, url, hooks):
        callback = hooks["response"]
        response = requests.Response()
        response.url = url
        response.status_code = 200
        petition_data = self.remote_data[int(self.id_from_url(url))]
        response.json = MagicMock(return_value=petition_data.as_dict)
        response.result = MagicMock(return_value=response)
        callback(response=response)
        return response

    def patch_future_session(self):
        import_path = f"{self.base_import_path}.RemotePetition.future_session"
        self.patches.future_session = mock.patch(import_path)
        self.mocks.future_session = self.patches.future_session.start()
        self.mocks.future_session.get = MagicMock(wraps=self.mock_future_get)
