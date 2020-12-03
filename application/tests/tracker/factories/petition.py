import faker, factory
from munch import Munch as ObjDict
from datetime import datetime as dt
from datetime import timedelta
from random import randint
from copy import deepcopy
import os, json, datetime, logging, random
from application.tests.conftest import init_faker
from application.tests import FROZEN_DATETIME

from application.tests.tracker.conftest import geography_keys
from application.tests.tracker.factories.signatures import SignaturesByFactory
from application.tests.tracker.conftest import (
    rand_range_or_int,
    get_geo_key,
    fetch_locales_for,
    rand_percent_locales,
    geography_names,
    geography_keys,
    uk_locale
)

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class PetitionFactory(ObjDict):

    fake = init_faker()
    signatures_by_factory = SignaturesByFactory

    @property
    def __query__(self):
        item = deepcopy(self.data)
        item.links = deepcopy(self.links)
        for key in geography_keys():
            item.attributes.pop(key, False)

        return item.__dict__

    @classmethod
    def build(cls, generic=0, custom=[], starting_id=0, default_values={}):
        if not generic and not custom:
            raise ValueError("generic count or custom configs must be provided")

        current_id = starting_id
        logger.info("building generic petitions")
        generic_built = []
        for item in range(generic):
            current_id += 1
            generic_built.append(cls(petition_id=current_id, **default_values))

        logger.info("building custom petitions")
        custom_built = []
        for config in custom:
            if not config.get("petition_id"):
                current_id += 1
                config["petition_id"]
            custom_built.append(cls(**{**default_values, **config}))

        return (generic_built + custom_built)

    @classmethod
    def auto_signatures_by(cls, **kwargs):
        config = {}
        for geo in geography_names():
            predef = kwargs.get("predef") or []
            undef =  kwargs.get("undef") or rand_percent_locales(geo)
            if geo == "country":
                UK = cls.signatures_by_factory.find_match("country", predef, uk_locale())
                UK = UK or dict(**uk_locale(), range="auto")
                predef.append(UK)

            config[geo] = {"locales": {"predef": predef, "undef": undef}}
        return config

    def __init__(self, petition_id, signature_count, signatures_by={}, state="open", **kwargs):
        self.make_base(petition_id, **kwargs)
        self.make_attr(signature_count, state, **kwargs)
        self.set_time(**kwargs)
        self.build_signatures(signature_count, signatures_by)

    def make_base(self, petition_id, timestamp=False, archived=False, **kwargs):
        self.data = ObjDict()
        self.links = ObjDict()
        self.data.attributes = ObjDict()

        if timestamp:
            self.archived = archived
            self.timestamp = timestamp.iso_format()

        self.make_links(petition_id, archived)
        self.data.id = petition_id
        self.data.type = "archived-petition" if archived else "petition"

    def make_links(self, petition_id, archived):
        base_url = "https://petition.parliament.uk"
        base_url += "/archived/petitions" if archived == "archived-petition" else "/petitions"
        self.links.self = f"{base_url}/{petition_id}.json"

    def build_signatures(self, signatures, geographies):
        if geographies is not False:
            if geographies == "auto":
                geographies = self.auto_signatures_by()
            if any(geographies):
                built = self.signatures_by_factory.build(signatures=signatures, **geographies)
            else:
                built = {k: [] for k in geography_keys()}

            self.data.attributes.update(built)

    def make_attr(self, signature_count, state, **kwargs):
        attrs = ObjDict()
        attrs.state = state
        attrs.creator_name = self.fake.name()
        attrs.action = self.fake.sentence(nb_words=15)
        attrs.background = self.fake.text(max_nb_chars=250)
        attrs.additional_details = self.fake.text(max_nb_chars=500)
        attrs.signature_count = rand_range_or_int(signature_count)

        self.data.attributes.update(attrs)

    def set_time(self, datetimes={}, **kwargs):
        state = self.data.attributes.state
        is_closed, is_rejected = (state == "closed"), (state == "rejected")
        will_respond = self.data.attributes.signature_count >= 10_000 and not is_rejected
        will_debate = self.data.attributes.signature_count >= 100_000 and not is_rejected

        attrs = ObjDict()
        attrs.created_at = datetimes.pop("created_at", None) or FROZEN_DATETIME
        attrs.opened_at = self.get_time_if(attrs.created_at, "days", [1, 14], True)
        attrs.rejected_at =  self.get_time_if(attrs.opened_at , "days", [1, 7], is_rejected)
        attrs.closed_at = (attrs.opened_at + timedelta(weeks=6)) if is_closed else None
        attrs.moderation_threshold_reached_at = self.get_time_if(attrs.opened_at, "hours", [1, 24], True)

        response_threshold = self.get_time_if(attrs.opened_at , "days", [2, 30], will_respond)
        have_responded =  random.choice([True, False]) and response_threshold
        attrs.response_threshold_reached_at = response_threshold
        attrs.government_response_at = self.get_time_if(response_threshold, "days", [30, 60], have_responded)

        debate_theshold = self.get_time_if(response_threshold, "days", [7, 60], will_debate)
        scheduled_debate = random.choice([True, False]) and debate_theshold
        have_debated = random.choice([True, False]) and scheduled_debate
        attrs.debate_theshold_reached_at = debate_theshold
        attrs.scheduled_debate_date = self.get_time_if(debate_theshold, "days", [30, 60], scheduled_debate)
        attrs.debate_outcome_at = self.get_time_if(attrs.scheduled_debate_date, "days", [1, 7], have_debated)

        iso_if_dt = lambda t: t.isoformat() if t and type(t) == dt else t
        attrs = {k: iso_if_dt(v) for k, v in dict(**attrs, **datetimes).items()}
        self.data.attributes.update(attrs)

    def get_time_if(self, prev_event, delta_unit, rand_range, condition):
        rand_time = timedelta(**{delta_unit: randint(*rand_range)})
        return (prev_event + rand_time) if condition else None