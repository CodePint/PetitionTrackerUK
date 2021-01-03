import pytest
from munch import Munch as ObjDict
from unittest.mock import MagicMock, PropertyMock, create_autospec
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from application.tracker.models import Petition
from application.tests.conftest import rkwargs
from application.tests.tracker.tests.models.conftest import TestPetitionModel
from application.tests.tracker.factories.petition import PetitionFactory
from application.tracker.models import Petition

from unittest import mock
from copy import deepcopy
from random import randrange
import os, json, logging, random

logger = logging.getLogger(__name__)



def configure_query_expr(cls, **kwargs):
    data = cls.create_data()
    cls.populated = cls.seed(data)
    cls.configure_trend_index()
    cls.configure_growth()
    cls.session.commit()

@pytest.mark.parametrize("class_session", [{"func": configure_query_expr}], indirect=True)
@pytest.mark.usefixtures("class_session")
class TestPetitionQueryExpr(TestPetitionModel):

    operands = {
        "signatures": 10_000,
        "growth_rate": 100,
        "trend_index": 5
    }

    expected_ids = {
        "signatures": {"lt": [1,2,3,4,5], "gt": [6,7,8,9,10]},
        "growth_rate": {"lt": [6,7,8,9,10], "gt": [1,2,3,4,5]},
        "trend_index": {"le": [1,3,5,7,9], "gt": [2,4,6,8,10]}
    }

    @classmethod
    def create_data(cls):
        threshold = cls.operands["signatures"]
        lt_count = {"signature_count": range(100, (threshold - 1))}
        gt_count = {"signature_count": range((threshold + 1), (threshold * 10))}
        lt_kwargs = [dict(petition_id=i, **lt_count) for i in cls.expected_ids["signatures"]["lt"]]
        gt_kwargs =  [dict(petition_id=i, **gt_count) for i in cls.expected_ids["signatures"]["gt"]]
        return cls.build(custom=(lt_kwargs + gt_kwargs))

    @classmethod
    def configure_growth(cls):
        threshold = cls.operands["growth_rate"]
        for petition in cls.query_ids(cls.expected_ids[f"growth_rate"]["lt"]).all():
            petition.growth_rate = random.randrange(10, (threshold - 1))
        for petition in cls.query_ids(cls.expected_ids[f"growth_rate"]["gt"]).all():
            petition.growth_rate = random.randrange((threshold + 1), 200)

    @classmethod
    def configure_trend_index(cls):
        trend_index = 0
        for key, ids in cls.expected_ids["trend_index"].items():
            for petition in cls.query_ids(ids).all():
                trend_index += 1
                petition.trend_index = trend_index

    @pytest.mark.parametrize("opr", [("lt"), ("gt")])
    def test_signatures_expressions(self, opr):
        query = Petition.query_expr(signatures={opr: self.operands["signatures"]})
        assert self.sorted_ids(query.all()) == self.expected_ids["signatures"][opr]

    @pytest.mark.parametrize("opr", [("lt"), ("gt")])
    def test_growth_expressions(self, opr):
        query = Petition.query_expr(growth_rate={opr: self.operands["growth_rate"]})
        assert self.sorted_ids(query.all()) == self.expected_ids["growth_rate"][opr]

    @pytest.mark.parametrize("opr", [("le"), ("gt")])
    def test_trend_index_expressions(self, opr):
        query = Petition.query_expr(trend_index={opr: self.operands["trend_index"]})
        assert self.sorted_ids(query.all()) == self.expected_ids["trend_index"][opr]

    def test_combined_expressions(self, min_sigs=500_000):
        min_index = self.operands["trend_index"]
        trending_ids = self.expected_ids["trend_index"]["le"]
        expected_ids = self.expected_ids["trend_index"]["le"][0:3]
        trending_pts = self.query_ids(trending_ids).all()
        expected_pts = self.query_ids(expected_ids).all()
        trending_pts = [p.update(signatures=randrange(1, 100)) for p in trending_pts]
        expected_pts = [p.update(signatures=randrange(min_sigs, (min_sigs * 2))) for p in expected_pts]
        self.session.commit()

        query = Petition.query_expr(signatures={"gt": min_sigs}, trend_index={"le": min_index})
        assert self.sorted_ids(query.all()) == expected_ids

