import pytest
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tests.tracker.factories.petition import PetitionFactoryManager
from application.tests.tracker.tests.views.conftest import TestTrackerViews
from application.tracker.models import Petition, Record
from freezegun import freeze_time
from unittest import mock
from datetime import timedelta
from datetime import datetime as dt
from copy import deepcopy
import os, json, uuid, random, logging

logger = logging.getLogger(__name__)


@freeze_time(FROZEN_TIME_STR)
class TestGetPetitionsWhere(TestTrackerViews):

    @classmethod
    def init_generic(cls, number, state, config, archived=False):
        config.update(state=state, archived=archived)
        data = cls.build(generic=number, starting_id=cls.starting_id, defaults=config)
        cls.petitions += cls.seed(data)
        cls.starting_id += number
        return cls.manage(data)

    @classmethod
    def init_custom(cls, configs):
        data = cls.build(custom=configs, starting_id=cls.starting_id)
        cls.petitions += cls.seed(data)
        cls.starting_id += len(configs)
        return cls.manage(data)

    @classmethod
    def init_dated(cls, number, state, base_config):
        dated_configs = []
        for i in range(1, number + 1):
            cls.created_at += timedelta(days=1)
            datetimes = {"created_at": cls.created_at}
            dated_configs.append({"state": state, "datetimes": datetimes, **base_config})

        return cls.init_custom(dated_configs)

    @classmethod
    def associate_petitions(cls):
        petition_managers = [m for managers in cls.managers.values() for m in managers]
        for manager in petition_managers:
            manager.petition = Petition.query.get(manager.petition_id)

    @classmethod
    def mark_text(cls, field):
        marker =  str(uuid.uuid1().int)
        for manager in cls.managers[field]:
            current_text = getattr(manager.petition, field)
            marked_text = current_text + " " + marker
            manager.petition.update(**{field: marked_text})

        cls.session.commit()
        return marker

    @classmethod
    def validate_query(cls, data, expectation, order_by=None):
        cls.order(expectation, order_by)
        for actual, expected in zip(data, expectation):
            assert actual["id"] == expected.petition_id
            assert cls.validate_petition(actual, actual["id"])
        return True

    @classmethod
    def order(cls, expectation, order_by):
        order_by = order_by or {"date": "DESC"}
        column, direction = list(order_by.items())[0]
        reverse = (direction == "DESC")
        get_val = lambda x: getattr(x.petition, column)
        expectation.sort(key=get_val, reverse=reverse)



def configure_test_get_where_state(cls, **kwargs):
    config = dict(signature_count=range(100, 100_000), signatures_by={"locales": "auto"})
    cls.petitions, cls.managers, cls.starting_id = [], {}, 0
    cls.managers["open"] = cls.init_dated(10, "open",  config)
    cls.managers["closed"] = cls.init_generic(3, "closed", config)
    cls.managers["rejected"] = cls.init_generic(3, "rejected", config)
    cls.managers["archived"] = cls.init_generic(3, "open", config, True)
    cls.managers["all_states"] = cls.managers["open"] + cls.managers["closed"] + cls.managers["rejected"]
    cls.associate_petitions()

@pytest.mark.parametrize("class_session", [{"func": configure_test_get_where_state}], indirect=True)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestGetPetitionsWhereStateOrderBy(TestGetPetitionsWhere):

    time_epoch = FROZEN_DATETIME - timedelta(days=365)
    created_at = time_epoch
    states = ["open", "closed", "rejected"]

    def run_test_with(self, app, params, expected, state, archived, order_by={"date": "DESC"}):
        if state in self.states:
            route = f"/petitions/{state}"
        else:
            route = "/petitions"

        response = app.test_client().get(route, query_string=self.to_qs(params))
        assert self.validate_status(response, 200)
        petitions = response.json["petitions"]

        validate_all = lambda key, exp: all(p[key] == exp for p in petitions)
        assert len(petitions) == len(expected)
        assert validate_all("archived", archived)
        assert (state not in self.states) or validate_all("state", state)
        assert self.validate_query(petitions, expected, order_by)

    @pytest.mark.parametrize(
        "state,order_by", [
            (None, {"signatures": "DESC"}),
            ("all", {"signatures": "ASC"}),
            ("open", None),
            ("open", {"date": "DESC"}),
            ("closed", {"action": "ASC"}),
            ("rejected", {"background": "DESC"})
        ]
    )
    def test_get_where_state(self, state, order_by, app, archived=False):
        params = {"order_by": order_by} if order_by else {}
        if state in self.states:
            expected = self.managers[state]
        else:
            expected = self.managers["all_states"]
        self.run_test_with(app, params, expected, state, archived, order_by)

    @pytest.mark.parametrize("archived", [(True), (False)])
    def test_get_where_archived(self, archived, app, state="open", order_by=None):
        params = {"archived": archived}
        expected = self.managers["archived"] if archived else self.managers[state]
        self.run_test_with(app, params, expected, state, archived, order_by)

    def test_invalid_state_returns_400(self, app, state="unknown"):
        response = app.test_client().get(f"/petitions/{state}")
        assert self.validate_status(response, 400)

    def test_where_no_petitions_found(self, app, state="open"):
        Petition.query.delete()
        self.session.commit()
        response = app.test_client().get(f"/petitions/{state}")
        assert self.validate_status(response, 200)
        assert response.json["petitions"] == []



def configure_test_get_where_text(cls, **kwargs):
    config = dict(signature_count=range(1000, 100_000), signatures_by={"locales": "auto"})
    cls.petitions, cls.managers, cls.starting_id = [], {}, 0
    cls.managers["generic"] = cls.init_generic(3, "open",  config)
    cls.managers["action"] = cls.init_generic(3, "open",  config)
    cls.managers["background"] = cls.init_generic(3, "open",  config)
    cls.managers["additional_details"] = cls.init_generic(3, "open",  config)
    cls.associate_petitions()

@pytest.mark.parametrize("class_session", [{"func": configure_test_get_where_text}], indirect=True)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestGetPetitionsWhereText(TestGetPetitionsWhere):


    @pytest.mark.parametrize(
        "fields", [
            (["action"]),
            (["background"]),
            (["additional_details"]),
            (["action", "background"]),
            (["additional_details", "background", "action"]),
        ]
    )
    def test_get_where_text_field(self, app, fields, state="open"):
        expected = []
        for f in fields:
            expected += self.managers[f]

        order_by = {fields[0]: "ASC"}
        route = f"/petitions/{state}"
        text_params = {k: self.mark_text(k) for k in fields}
        params = {"order_by": order_by, "text": text_params}

        response = app.test_client().get(f"/petitions/{state}", query_string=self.to_qs(params))
        assert self.validate_status(response, 200)

        petitions = response.json["petitions"]
        for k, v in text_params.items():
            assert all([v in p[k] for p in petitions])

        assert self.validate_query(petitions, expected, order_by)



def configure_test_get_where_expressions(cls, **kwargs):
    config = dict(signature_count=range(100, 1000), signatures_by={"locales": "auto"})
    strft_created_at = lambda t: (cls.created_at + timedelta(hours=t)).strftime("%d-%m-%YT%H:%M:%S")
    cls.petitions, cls.managers, cls.expressions, cls.starting_id = [], {}, {}, 0

    cls.managers["date_lt"] = cls.init_dated(3, "open",  config)
    cls.expressions["date_lt"] = {"date": {"lt": strft_created_at(12)}}

    config["signature_count"] = range(1001, 100_000)

    cls.expressions["date_lt_and_signatures_gt"] = {}
    cls.managers["date_lt_and_signatures_gt"] = cls.init_dated(3, "open",  config)
    cls.expressions["date_lt_and_signatures_gt"]["date"] = {"lt": strft_created_at(12)}
    cls.expressions["date_lt_and_signatures_gt"]["signatures"] = {"gt": min(config["signature_count"])}

    cls.managers["signatures_gt"] = cls.init_dated(3, "open",  config)
    cls.managers["signatures_gt"] += cls.managers["date_lt_and_signatures_gt"]
    cls.expressions["signatures_gt"] = {"signatures": {"gt": min(config["signature_count"])}}
    cls.associate_petitions()

@pytest.mark.parametrize("class_session", [{"func": configure_test_get_where_expressions}], indirect=True)
@pytest.mark.usefixtures("class_session")
@freeze_time(FROZEN_TIME_STR)
class TestGetPetitionsWhereExpressions(TestGetPetitionsWhere):

    time_epoch = FROZEN_DATETIME - timedelta(days=365)
    created_at = time_epoch

    @pytest.mark.parametrize(
        "expression", [
            ("date_lt"),
            ("signatures_gt"),
            ("date_lt_and_signatures_gt"),
        ]
    )
    def test_get_where_expression(self, expression, app, state="open", archived=False):
        route = f"/petitions/{state}"
        order_by = {"date": "ASC"}
        expressions = self.expressions[expression]
        expected = self.managers[expression]
        params = {"expressions": self.expressions[expression], "order_by": order_by}

        response = app.test_client().get(f"/petitions/{state}", query_string=self.to_qs(params))
        assert self.validate_status(response, 200)
        petitions = response.json["petitions"]

        assert self.validate_query(petitions, expected, {"date": "ASC"})