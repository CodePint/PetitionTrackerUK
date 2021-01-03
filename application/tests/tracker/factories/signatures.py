import numpy
from numpy.random import multinomial, dirichlet
from copy import deepcopy
from munch import Munch as ObjDict
from random import randint, randrange
from datetime import datetime as dt
from copy import deepcopy
import os, json, logging
from application.tests.tracker.conftest import rand_percent_locales
from application.tracker.geographies.dictionaries.regions import REGIONS
from application.tracker.geographies.dictionaries.countries import COUNTRIES
from application.tracker.geographies.dictionaries.constituencies import CONSTITUENCIES

logger = logging.getLogger(__name__)



class SignaturesByFactory():

    UK = {"code": "GB", "name": "United Kingdom"}
    geographies = ["region", "country", "constituency"]
    auto_range = range(65, 90)

    def __repr__(self):
        return str(self.__dict__)

    @property
    def __dict__(self):
        return self.locales.get("initialized", [])

    @classmethod
    def get_key(cls, geo):
        return f"signatures_by_{geo}"

    @classmethod
    def get_geo(cls, key):
        return key.replace("signatures_by_", "")

    @classmethod
    def make_config(cls, locales=1):
        config = {}
        for geo in cls.geographies:
            predef = [cls.UK.copy()] if geo == "country" else []
            undef = rand_percent_locales(geo) if locales == "auto" else locales
            config[geo] = {"locales": {"undef": undef, "predef": predef}}
        return config

    @classmethod
    def build(cls, signatures, region, country, constituency):
        logger.info(f"executing SignaturesByFactory build")
        config = cls.setup_build(region, country, constituency, signatures)
        return ObjDict({cls.get_key(geo): cls(geo, **conf).__dict__ for geo, conf in config.items()})

    @classmethod
    def increment(cls, count, previous, future):
        config = {}
        for key, previous_locations in deepcopy(previous).items():
            geography = cls.get_geo(key)
            future_undef = future[geography]["locales"].get("undef", 0)
            future_predef = future[geography]["locales"].get("predef", [])

            for prev_locale in previous_locations:
                future_locale = cls.find_match(geography, future_predef, prev_locale)
                prev_locale.pop("signature_count")
                if future_locale:
                    prev_locale["signature_count"] = future_locale["signature_count"]
                future_predef.append(prev_locale)

            config[geography] = {"locales": {"predef": future_predef, "undef": future_undef}}

        incremented = cls.build(signatures=count, **config)
        merged = cls.update(previous=previous, future=incremented)
        return merged

    @classmethod
    def update(cls, previous, future):
        merged = {}
        for key, locations in future.items():
            merged[key] = []
            for future_locale in locations:
                geo = cls.get_geo(key)
                previous_locale = cls.find_match(geo, previous[key], future_locale, fallback={})
                future_locale["signature_count"] += previous_locale.get("signature_count", 0)
                merged[key].append(future_locale)
        return merged

    @classmethod
    def setup_build(cls, region, country, constituency, signatures):
        national = cls.configure_uk(country, signatures)
        return {
            "country": dict(**country, signatures=signatures),
            "region": dict(**region, signatures=national),
            "constituency": dict(**constituency, signatures=national)
        }

    @classmethod
    def configure_uk(cls, country, total):
        UK = cls.find_match("country", country["locales"]["predef"], cls.UK)
        if not UK:
            raise ValueError("UK not in predefined countries")

        UK["signature_count"] = UK.get("signature_count") or cls.random_ranged_ratio(total, UK.pop("range", "auto"))
        if UK["signature_count"] > total:
            raise ValueError("National count greater than total count")

        return UK["signature_count"]

    def pre_validate(self):
        if not self.locales["predef"] and not self.locales["undef"]:
            raise ValueError(f"{self.geography} does not have any locales defined")
        if not self.locales_are_unique(self.locales["predef"]):
            raise ValueError(f"{self.geography} has dupliate predef locales")

    # locales => dict {"predef": [], "undef": 0}
    def __init__(self, geography, signatures, locales):
        self.geography = geography
        self.signatures = signatures
        self.locales = locales
        self.configure()

        self.pre_validate()
        self.init_predef()
        self.init_undef()
        self.post_validate()

    def post_validate(self):
        counts = [locale["signature_count"] for locale in self.locales["initialized"]]
        if sum(counts) != self.signatures:
            raise ValueError(f"{self.geography} locale counts != signatures count")

    def configure(self):
        self.locales["initialized"] = []
        self.locales["predef"] = deepcopy(self.locales.get("predef", []))
        self.locales["undef"] = self.locales.get("undef", 0)
        self.locales["source"] = self.source_locales(self.geography)
        self.locales["counts"] = self.create_counts()

    def create_counts(self):
        counts = [locale["signature_count"] for locale in self.locales["predef"] if locale.get("signature_count")]
        length = ((len(self.locales["predef"]) - len(counts)) + self.locales["undef"])
        remainder = self.signatures - sum(counts)
        try:
            return self.random_locale_counts(remainder, length)
        except ValueError as e:
            raise ValueError(f"total signatures ({self.signatures}) less than predef counts") from e

    def init_predef(self, **kwargs):
        source = []
        predef = self.alphabetize_locales(self.locales["predef"], self.geography)
        for location in self.locales["source"]:
            match = self.find_match(self.geography, predef, location)
            if not match:
                source.append(location)
                continue

            location["signature_count"] = match.get("signature_count") or self.locales["counts"].pop(0)
            self.locales["initialized"].append(location)
            predef.pop(predef.index(match))

        if any(predef):
            raise ValueError(f"invalid locales(s): {predef}")

        self.locales["source"] = source

    def init_undef(self, **kwargs):
        for location in range(self.locales["undef"]):
            location = self.pop_random_locale()
            location["signature_count"] = self.locales["counts"].pop(0)
            self.locales["initialized"].append(location)

        if any(self.locales["counts"]):
            raise ValueError(f"excess locale counts {self.locales['counts']}")

    def pop_random_locale(self):
        return self.locales["source"].pop(randrange(len(self.locales["source"])))

    @classmethod
    def locales_are_unique(cls, locations):
        values = cls.get_locale_values(locations)
        return (len(values) == len(set(values)))

    @classmethod
    def get_locale_values(cls, locations):
        values = []
        for locale in locations:
            for k, v in locale.items():
                if k != "signature_count":
                    values.append(v)
        return values

    @classmethod
    def is_uk(cls, locale, geography="country"):
        return cls.is_match(geography, cls.UK, locale)

    @classmethod
    def random_ranged_ratio(cls, total, _range):
        _range = cls.auto_range if _range == "auto" else _range
        return round(total * cls.random_ranged_decimal(_range))

    @classmethod
    def random_locale_counts(cls, total, length):
        return [int(i) for i in list(multinomial(total, dirichlet(numpy.ones(length), 1)[0]))]

    @classmethod
    def random_ranged_decimal(cls, _range):
        return (randint(min(_range), max(_range)) / 100)

    @classmethod
    def alphabetize_locales(cls, locales, geo):
        code_key = cls.get_code_key(geo)
        return sorted(locales, key=lambda x: x.get(code_key) or x.get("name"))

    @classmethod
    def find_match(cls, geo, source, target, fallback=None):
        return next(iter(filter(lambda item: cls.is_match(geo, item, target), source)), fallback)

    @classmethod
    def get_code_key(cls, geo):
        return "code" if geo == "country" else "ons_code"

    @classmethod
    def is_match(cls, geo, locale, target):
        code_key, name_key = cls.get_code_key(geo), "name"
        matched_code = locale.get(code_key) == target.get(code_key)
        matched_name = locale.get(name_key) == target.get(name_key)
        return bool(matched_code or matched_name)

    @classmethod
    def source_locales(cls, geo):
        geographies = {
            "region": REGIONS,
            "country": COUNTRIES,
            "constituency": CONSTITUENCIES
        }

        try:
            return deepcopy(geographies[geo])
        except KeyError:
            raise ValueError(f"invalid geography argument: {geo}")