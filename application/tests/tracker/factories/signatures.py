import numpy
from numpy.random import multinomial, dirichlet
from copy import deepcopy
from munch import Munch as ObjDict
from random import randint, randrange
from datetime import datetime as dt
from copy import deepcopy
import os, json, logging

from application.tracker.geographies.dictionaries.regions import REGIONS
from application.tracker.geographies.dictionaries.countries import COUNTRIES
from application.tracker.geographies.dictionaries.constituencies import CONSTITUENCIES

logger = logging.getLogger(__name__)

class SignaturesByFactory(ObjDict):

    UK = {"code": "GB", "name": "United Kingdom"}
    geographies = ["region", "country", "constituency"]
    auto_range = range(65, 90)

    def __repr__(self):
        return str(self.__dict__)

    @property
    def __dict__(self):
        return self.locales.get("initialized", [])

    @classmethod
    def build(cls, signatures, region, country, constituency):
        logger.info(f"Beginning SignaturesByFactory build")
        configs = cls.configure_build(region, country, constituency, signatures)
        key = lambda geo: f"signatures_by_{geo}"
        return ObjDict({key(geo): SignaturesByFactory(geo, **conf).__dict__ for geo, conf in configs.items()})

    # locales => dict {"predef": [], "undef": 0}
    def __init__(self, geography, signatures, locales):
        self.geography = geography
        self.signatures = signatures
        self.locales = locales

        self.pre_validate()
        self.configure()
        self.init_predef()
        self.init_undef()
        self.post_validate()

    def configure(self):
        logger.info(f"configuring locales: {self.locales}")

        self.locales["initialized"] = []
        self.locales["predef"] = deepcopy(self.locales.get("predef", []))
        self.locales["undef"] = self.locales.get("undef", 0)
        self.locales["source"] = self.source_locales(self.geography)
        self.locales["counts"] = self.create_counts()

    def pre_validate(self):
        logger.info("validating locales")
        if not self.locales["predef"] and not self.locales["undef"]:
            raise ValueError(f"{self.geography} does not have any locales defined")
        if not self.locales_are_unique(self.locales["predef"]):
            raise ValueError(f"{self.geography} has dupliate predef locales")

    def create_counts(self):
        logger.info("creating locale counts")
        counts = [locale["count"] for locale in self.locales["predef"] if locale.get("count")]
        length = ((len(self.locales["predef"]) - len(counts)) + self.locales["undef"])
        remainder = self.signatures - sum(counts)
        try:
            created = self.random_locale_counts(remainder, length)
            logger.info(f"locale counts: {created}")
            return created
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

            location["count"] = match.get("count") or self.locales["counts"].pop(0)
            self.locales["initialized"].append(location)
            predef.pop(predef.index(match))

        if any(predef):
            raise ValueError(f"invalid locales(s): {predef}")

        self.locales["source"] = source
        logger.info(f"predef locales(s) initialized: {self.locales['initialized']}")

    def init_undef(self, **kwargs):
        for location in range(self.locales["undef"]):
            location = self.pop_random_locale()
            location["count"] = self.locales["counts"].pop(0)
            self.locales["initialized"].append(location)

        if any(self.locales["counts"]):
            raise ValueError(f"excess locale counts {self.locales['counts']}")

        logger.info(f"undef locales(s) initialized: {self.locales['initialized']}")

    def pop_random_locale(self):
        return self.locales["source"].pop(randrange(len(self.locales["source"])))

    def post_validate(self):
        counts = [locale["count"] for locale in self.locales["initialized"]]
        if sum(counts) != self.signatures:
            raise ValueError(f"{self.geography} initialized locale counts != signatures count")

    @classmethod
    def configure_build(cls, region, country, constituency, signatures):
        national = cls.configure_uk(signatures, country)
        return {
            "country": dict(**country, signatures=signatures),
            "region": dict(**region, signatures=national),
            "constituency": dict(**constituency, signatures=national)
        }

    @classmethod
    def configure_uk(cls, total, country):
        UK = cls.find_match("country", country["locales"]["predef"], cls.UK)
        if not UK:
            raise ValueError("UK not in predefined countries")

        UK["count"] = UK.get("count") or cls.random_ranged_ratio(total, UK.pop("range"))
        if UK["count"] > total:
            raise ValueError("National count greater than total count")

        return UK["count"]

    @classmethod
    def locales_are_unique(cls, locations):
        values = cls.get_locale_values(locations)
        return (len(values) == len(set(values)))

    @classmethod
    def get_locale_values(cls, locations):
        values = []
        for locale in locations:
            for k, v in locale.items():
                if k != "count":
                    values.append(v)
        return values

    @classmethod
    def is_uk(cls, locale):
        return cls.is_match("country", cls.UnitedKingdom, locale)

    @classmethod
    def random_ranged_ratio(cls, total, _range):
        _range = cls.auto_range if _range == "auto" else _range
        return round(total * cls.random_ranged_decimal(_range))

    @classmethod
    def random_locale_counts(cls, total, length):
        return list(multinomial(total, dirichlet(numpy.ones(length), 1)[0]))

    @classmethod
    def random_ranged_decimal(cls, _range):
        return (randint(min(_range), max(_range)) / 100)

    @classmethod
    def alphabetize_locales(cls, locales, geo):
        code_key, name_key = cls.get_code_key(geo), "name"
        return sorted(locales, key=lambda x: x.get(code_key) or x.get(name_key))

    @classmethod
    def find_match(cls, geo, source, target):
        return next(iter(filter(lambda item: cls.is_match(geo, item, target), source)), None)

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