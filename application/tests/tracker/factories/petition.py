import faker, factory
from munch import Munch as ObjDict
from freezegun import freeze_time
from datetime import datetime as dt
from datetime import timedelta
from random import randint
from copy import deepcopy
from collections import OrderedDict
import os, json, datetime, logging, random, datetime
from application.tests.conftest import init_faker
from application.tests import FROZEN_DATETIME
from application.tracker.models import Petition, Record
from application.tests.tracker.conftest import geography_keys
from application.tests.tracker.factories.signatures import SignaturesByFactory
from application.tests.tracker.factories.config import TIMELINE_CONFIG
from application.tests.tracker.conftest import (
    rand_range_or_int,
    get_geo_key,
    fetch_locales_for,
    rand_percent_locales,
    geography_names,
    geography_keys,
    uk_locale,
    iso_if_dt,
    try_strptime,
    geography_lengths
)

logger = logging.getLogger(__name__)
logger.setLevel("INFO")



class PetitionFactory(ObjDict):

    fake = init_faker()
    signatures_by_factory = SignaturesByFactory

    @property
    def as_query(self):
        petition = {}
        data = self.as_dict["data"]
        attributes = data.pop("attributes")
        petition.update(data)
        petition.update(attributes)
        petition["links"] = self.links.__dict__
        for key in geography_keys():
            petition.pop(key, None)

        return petition

    @property
    def as_dict(self):
        serialized = self.__dict__
        serialized_attributes = {k: iso_if_dt(v) for k, v in serialized["data"]["attributes"].items()}
        serialized["data"]["attributes"].update(serialized_attributes)
        return serialized

    def print_timeline(self):
        for k, v in self.timeline.items():
            print(f"name: {k}, date: {v}")

    @property
    def timeline(self):
        dates = filter(lambda x: type(x[1]) is dt, self.data.attributes.items())
        return OrderedDict(sorted(list(dates)))

    @property
    def archived(self):
        return True if self.data.type == "archived-petition" else False

    @property
    def signature_count(self):
        return self.getattr("signature_count")

    @property
    def signatures_by(self):
        return {k: v for k, v in self.data.attributes.items() if k.startswith("signatures_by")}

    @property
    def state(self):
        return self.getattr("state")

    def setattr(self, key, val, lazy=False):
        self.data.attributes[key] = self.getattr(key, fallback=val) if lazy else val

    def getattr(self, key, fallback=None):
        return self.data.attributes.get(key, fallback)

    @classmethod
    def build(cls, generic=0, custom=None, starting_id=0, defaults=None):
        defaults = defaults or {}
        custom = custom or []
        if not generic and not custom:
            raise ValueError("generic count or custom configs must be provided")

        current_id = starting_id
        logger.info("building generic petitions")
        generic_built = []
        for item in range(generic):
            current_id += 1
            generic_built.append(cls(petition_id=current_id, **deepcopy(defaults)))

        logger.info("building custom petitions")
        custom_built = []
        for config in custom:
            if not config.get("petition_id"):
                current_id += 1
                config["petition_id"] = current_id
            custom_built.append(cls(**{**deepcopy(defaults), **config}))

        return (generic_built + custom_built)

    def __init__(self, petition_id, signature_count, state="open", archived=False, datetimes=None, signatures_by=None):
        self.make_base(petition_id, archived)
        self.make_attributes(signature_count, state)
        self.make_timeline(datetimes)
        self.make_signatures(signatures_by)

    def make_base(self, petition_id, archived=False):
        self.data = ObjDict(attributes=ObjDict())
        self.data.id = petition_id
        self.set_type(archived)
        self.make_links()

    def set_type(self, archived):
        self.data.type = "archived-petition" if archived else "petition"

    def make_links(self):
        self.links = ObjDict()
        base_url = "https://petition.parliament.uk"
        base_url += "/archived/petitions" if self.archived else "/petitions"
        self.links.self = f"{base_url}/{self.data.id}.json"

    def make_signatures(self, signatures_by):
        signatures_by = signatures_by or {}
        locales = signatures_by.pop("locales", None)
        if signatures_by or locales:
            if locales:
                signatures_by = self.signatures_by_factory.make_config(locales)
            signatures_by["signatures"] = self.getattr("signature_count")
            built = self.signatures_by_factory.build(**signatures_by)
        else:
            built = {k: [] for k in geography_keys()}

        self.data.attributes.update(built)

    def make_attributes(self, signature_count, state):
        self.setattr("state", state)
        self.setattr("creator_name", self.fake.name())
        self.setattr("action", self.fake.sentence(nb_words=15))
        self.setattr("background", self.fake.text(max_nb_chars=250))
        self.setattr("additional_details", self.fake.text(max_nb_chars=500))
        self.setattr("signature_count", rand_range_or_int(signature_count))

    def make_timeline(self, overrides):
        overrides = overrides or {}
        self.setattr("created_at", overrides.get("created_at", FROZEN_DATETIME), lazy=True)
        for config in TIMELINE_CONFIG():
            config = overrides.get(config["name"]) or config
            if not self.getattr(config["name"]):
                self.setattr(config["name"], self.handle_date(**config))

        self.setattr("updated_at", list(self.timeline.values())[-1])

    def find_updated_at(self):
        return sorted(list(filter(lambda item: type(item) is dt, self.data.attributes.values())))[-1]

    def handle_date(self, name, states, increment_by, preceeded_by, **kwargs):
        increment_date = lambda pre, incr: pre + timedelta(**{incr["unit"]: randint(*incr["range"])})

        conditions = []
        conditions.append((self.getattr("state") in states) if ("any" not in states) else True)
        conditions.append(self.getattr("signature_count") >= kwargs.get("minimum_signatures", 0))
        conditions.append(random.randrange(0, 100) < kwargs.get("probability", 100))

        preceeded_by = self.getattr(preceeded_by, fallback=preceeded_by)
        dependant_on = [self.getattr(attr) for attr in kwargs.get("dependant_on", [])]

        if all(dependant_on) and all(conditions):
            return increment_date(preceeded_by, increment_by)


class PetitionFactoryManager():

    signatures_by_factory = SignaturesByFactory

    @property
    def current(self):
        return self.timeline[self.current_index]

    def __init__(self, petition, meta=None):
        self.petition_id = petition.data.id
        self.current_index = 0
        self.timeline = []
        self.timeline.append(ObjDict(petition=deepcopy(petition), updates={}, meta=meta or {}))

    def increment(self, count, commit=False, records=False, meta=None, **kwargs):
        update = {}
        update["datetimes"] = kwargs.get("datetimes", {})
        update["attributes"] = kwargs.get("attributes", {})
        update["archived"] = kwargs.get("archived", None)

        default_sigs_by = lambda d: {k: d.get(k, {"locales": {}}) for k in geography_names()}
        update["signatures_by"] = default_sigs_by(kwargs.get("signatures_by", {}))

        count = rand_range_or_int(count)
        previous_entry = self.timeline[self.current_index]
        future_entry = self.update(previous=previous_entry, increment=count, meta=meta, **update)
        signatures_by = self.signatures_by_factory.increment(
            previous=previous_entry.petition.signatures_by,
            future=update["signatures_by"],
            count=count,
        )
        future_entry.petition.data.attributes.update(signatures_by)

        if commit:
            session = kwargs["session"]
            self.sync_petition(session, future_entry, kwargs["timestamp"])
            if records:
                self.save_records(session, future_entry, **records)
            session.commit()

        self.timeline.append(future_entry)
        self.current_index += 1
        return future_entry.petition

    def update(self, previous, increment, signatures_by, archived, datetimes, meta, attributes):
        future = ObjDict(meta=meta or {}, petition=deepcopy(previous.petition))
        future.updates = {"increment": increment, "signatures_by": signatures_by, "attributes": attributes}
        future.petition.setattr("signature_count", previous.petition.signature_count + increment)
        if previous.petition.signature_count > future.petition.signature_count:
            raise ValueError("previous signatures less than future signatures")

        future.petition.set_type(archived or previous.petition.archived)
        future.petition.make_links()
        future.petition.make_timeline(datetimes)
        future.petition.data.attributes.update(attributes)

        return future

    def sync_petition(self, session, entry, polled_at):
        self.petition = Petition.query.get(self.petition_id)
        self.petition.sync(data=entry.petition.as_dict, timestamp=polled_at)
        session.commit()

    def save_records(self, session, entry, base=None, geo=None):
        base, geo = base or {}, geo or{}
        entry.records = ObjDict()
        params = {
            "petition_id": self.petition.id,
            "signatures": self.petition.signatures,
            "timestamp": self.petition.polled_at
        }

        if base.pop("save", False):
            entry.records.base = Record(**dict(**params, **base))
            session.add(entry.records.base)
            session.flush()
        if geo.pop("save", False):
            entry.records.geo = Record(**dict(**params, **base))
            session.add(entry.records.geo)
            session.flush()
            attributes = self.petition.latest_data["data"]["attributes"]
            signatures_by = entry.records.geo.build(attributes)
            session.bulk_save_objects(signatures_by)

        session.commit()

    def clear_db_attrs(self):
        if hasattr(self, "petition"):
            delattr(self, "petition")
        for entry in self.timeline:
            entry.pop("records", None)
