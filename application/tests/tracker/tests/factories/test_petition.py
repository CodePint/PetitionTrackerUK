import pytest
from faker import Faker, providers
from freezegun import freeze_time
from munch import Munch as ObjDict
from unittest import mock
from unittest.mock import MagicMock
from datetime import timedelta
from datetime import datetime as dt
from random import randint, randrange
from contextlib import contextmanager
from copy import deepcopy
import os, json, logging, random

from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.conftest import get_kwargs
from application.tests.tracker.conftest import (
    fetch_locales_for,
    rand_percent_locales,
    geography_names,
    geography_keys
)

petition_factory_path = "application.tests.tracker.factories.petition"
from application.tests.tracker.factories.petition import PetitionFactory


logger = logging.getLogger(__name__)

class TestPetitionFactory():

    import_path = petition_factory_path
    base_url = "https://petition.parliament.uk/petitions"
    base_archive_url = "https://petition.parliament.uk/archived/petitions"

    @pytest.fixture(autouse=True, scope="function")
    def context(self):
        self.patches = ObjDict()
        self.mocks = ObjDict()
        self.patch_petition_fake()
        self.patch_signatures_build()

        yield

        for p in self.patches.values(): p.stop()

    def patch_petition_fake(self):
        Faker.seed(providers.lorem)
        import_path = f"{self.import_path}.PetitionFactory.fake"
        self.patches.faker = mock.patch(import_path, wraps=Faker())
        self.mocks.faker = self.patches.faker.start()

    def patch_signatures_build(self):
        import_path = f"{self.import_path}.SignaturesByFactory.build"
        self.patches.signature_build = mock.patch(import_path)
        self.mocks.signature_build = self.patches.signature_build.start()
        self.mocks.signature_build.return_value = self.signature_build_return()

    @classmethod
    def signature_build_return(cls):
        return ObjDict(
            signatures_by_region=[{"a": "b"}],
            signatures_by_country=[{"c": "d"}],
            signatures_by_constituency=[{"e": "f"}]
        )

    @classmethod
    def total_signatures_fallback(cls):
        return randint(500, 200_000)

    @pytest.fixture(scope="function")
    def petition_kwargs(self, request):
        kwargs = get_kwargs(request)
        self.kwargs = ObjDict({
            "petition_id": kwargs.get("petition_id", 999_999),
            "signature_count": kwargs.get("count") or self.total_signatures_fallback(),
            "state": kwargs.get("state", "open"),
            "archived":  kwargs.get("archived", False),
        })
        if kwargs.get("signatures_by") is not None:
            self.kwargs["signatures_by"] = kwargs["signatures_by"]

    @pytest.fixture(scope="function")
    def signatures_by_kwargs(self, request):
        self.kwargs["signatures_by"] = {}

        for geo in geography_names():
            predef = fetch_locales_for(geo, count=5)
            locales = {"predef": predef, "undef": rand_percent_locales(geo)}
            self.kwargs["signatures_by"][geo] = {"locales": locales}

        return deepcopy(self.kwargs["signatures_by"])

    def validate(self):
        self.attrs = self.petition.data.attributes
        assert self.validate_dict()
        assert self.validate_input()
        assert self.validate_archived()
        assert self.validate_links()
        assert self.validate_fakes()
        return True

    def validate_dict(self):
        assert self.petition.__dict__ == self.petition
        return True

    def validate_fakes(self):
        faked_values = ["action", "creator_name", "background", "additional_details"]
        for key in faked_values:
            assert type(self.attrs[key]) == str

        assert self.mocks.faker.name.call_count == 1
        assert self.mocks.faker.sentence.call_count == 1
        assert self.mocks.faker.text.call_count == 2
        return True

    def validate_input(self):
        assert self.petition.data.id == self.kwargs.petition_id
        assert self.petition.data.attributes.state == self.kwargs.state
        if type(self.kwargs.signature_count) is range:
            assert self.attrs.signature_count in self.kwargs.signature_count
        else:
            assert self.attrs.signature_count == self.kwargs.signature_count
        return True

    def validate_archived(self):
        if self.kwargs.archived:
            assert self.petition.data.type == "archived-petition"
            self.expected_base_url = self.base_archive_url
        else:
            assert self.petition.data.type == "petition"
            self.expected_base_url = self.base_url
        return True

    def validate_links(self):
        expected_link =  f"{self.expected_base_url }/{self.kwargs.petition_id}.json"
        assert self.petition.links.self == expected_link
        return True



class TestPetitionFactoryData(TestPetitionFactory):
    @pytest.mark.parametrize('petition_kwargs', [{"count": range(10, 1000)}], indirect=True)
    def test_when_signature_count_is_a_range(self, petition_kwargs):
        self.petition = PetitionFactory(**self.kwargs)
        assert self.validate()

    @pytest.mark.parametrize('petition_kwargs', [{"count": 100}], indirect=True)
    def test_when_signatures_count_is_an_int(self, petition_kwargs):
        self.petition = PetitionFactory(**self.kwargs)
        assert self.validate()

    @pytest.mark.parametrize('petition_kwargs', [{"count": 1000, "signatures_by": {}}], indirect=True)
    def test_when_state_signatures_by_is_empty(self, petition_kwargs):
        self.petition = PetitionFactory(**self.kwargs)
        assert self.validate()
        for key in geography_keys():
            assert self.petition.__dict__["data"]["attributes"][key] == []

    @pytest.mark.parametrize('petition_kwargs', [{"count": 1000, "signatures_by": False}], indirect=True)
    def test_when_signatures_by_is_False(self, petition_kwargs):
        self.petition = PetitionFactory(**self.kwargs)
        assert self.validate()
        for key in geography_keys():
            assert key not in self.petition.__dict__["data"]["attributes"]

    @pytest.mark.parametrize('petition_kwargs', [{"count": 1000}], indirect=True)
    def test_when_signatures_by_is_provided(self, petition_kwargs, signatures_by_kwargs):
        self.petition = PetitionFactory(**self.kwargs)
        assert self.validate()

        expected_call_kwargs = dict(signatures=self.kwargs["signature_count"],  **signatures_by_kwargs)
        self.mocks.signature_build.assert_called_once_with(**expected_call_kwargs)
        for key in geography_keys():
            expected = self.signature_build_return()[key]
            actual = self.petition.__dict__["data"]["attributes"][key]
            assert actual == expected

