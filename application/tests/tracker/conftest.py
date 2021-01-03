import pytest
from freezegun.api import FakeDatetime
from application.tests.conftest import rkwargs
from copy import deepcopy
from random import randint, randrange
from datetime import datetime as dt
import os, logging, random

from application.tracker.geographies.dictionaries.regions import REGIONS as REGIONS_LIST_DICT
from application.tracker.geographies.dictionaries.countries import COUNTRIES as COUNTRIES_LIST_DICT
from application.tracker.geographies.dictionaries.constituencies import CONSTITUENCIES as CONSTITUENCIES_LIST_DICT
from application.tracker.geographies.python.regions import REGIONS as REGIONS_DICT
from application.tracker.geographies.python.countries import COUNTRIES as COUNTRIES_DICT
from application.tracker.geographies.python.constituencies import CONSTITUENCIES as CONSTITUENCIES_DICT

logger = logging.getLogger(__name__)

## geography sources
def geography_vers(key):
    vers = {
        "list": {
            "region": REGIONS_LIST_DICT,
            "country": COUNTRIES_LIST_DICT,
            "constituency": CONSTITUENCIES_LIST_DICT
        },
        "dict":{
            "region": REGIONS_DICT,
            "country": COUNTRIES_DICT,
            "constituency": CONSTITUENCIES_DICT
        }
    }
    return deepcopy(vers[key])

get_geo_key = lambda geo: f"signatures_by_{geo}"
geography_names = lambda: ["constituency", "country", "region"]
geography_keys = lambda: sorted([get_geo_key(geo) for geo in geography_names()])
geography_lengths = lambda: {g: len(l) for g, l in geography_vers("list").items()}

# geography lambdas
uk_locale = lambda: {"code": "GB", "name": "United Kingdom"}
get_code_key = lambda geo: "code" if geo == "country" else "ons_code"
list_of_counts = lambda locales: [loc.get("signature_count") for loc in locales if loc.get("signature_count")]
list_with_counts = lambda locales: [loc for loc in locales if loc.get("signature_count")]
get_geo_src = lambda fmt: {geo: copy_geo_src(geo, fmt) for geo in geography_names()}

# generic lambdas
iso_if_dt = lambda t: t.isoformat() if t and isinstance(t, (FakeDatetime, dt)) else t
invert_dict = lambda d: {v: k for k, v in d.items()}
rand_range_or_int = lambda v: randint(min(v), max(v)) if type(v) is range else int(v)
rand_pop = lambda src: src.pop(randrange(len(src)))

## helper functions
def raiser(ex, msg, **kwargs):
    raise ex(msg, **kwargs)

def try_strptime(val, fmt):
    if fmt == "iso":
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
    try:
        return val.strptime(fmt)
    except ValueError:
        return val

def rand_percent_locales(geo, percentage=None, used=0):
    default_percentage = range(20, 50) if geo == "region" else range(1, 25)
    multiplier = rand_range_or_int(percentage or default_percentage)
    available = (geography_lengths()[geo] - used)
    hundreth = (available / 100)
    result = round(hundreth * multiplier)
    return result if result <= available else raiser(ValueError, "percentage > available")

def dict_of_counts(geo, locales):
    code_key = get_code_key(geo)
    locales = [loc for loc in locales if loc.get("signature_count")]
    return {loc.get(code_key) or loc.get("name"): loc["signature_count"] for loc in locales}

def is_locale_match(geo, locale, target):
    code_key, name_key = get_code_key(geo), "name"
    matched_code = locale.get(code_key) == target.get(code_key)
    matched_name = locale.get(name_key) == target.get(name_key)
    return bool(matched_code or matched_name)

def find_locale(geo, source, target):
    return next(iter(filter(lambda item: is_locale_match(geo, item, target), source)), None)

def exclude_locale(geo, source, target):
    return list(filter(lambda item: not is_locale_match(geo, item, target), source))

def copy_geo_src(geo, fmt="list"):
    src = geography_vers(fmt)
    return deepcopy(src[geo])

def fetch_locales_for(geo, locales=None, count=0):
    fetched = []
    source = copy_geo_src(geo)

    if locales:
        fetched += [find_locale(geo, source, target) for target in (locales)]
    if count:
        fetched += [rand_pop(source) for i in range(count)]

    return fetched or source

## fixtures
@pytest.fixture(scope="function")
def geo_src_list(request):
    return get_geo_src(fmt="list")

@pytest.fixture(scope="function")
def geo_src_dict(request):
    return get_geo_src(fmt="dict")

@pytest.fixture(scope="function")
def region_src(request):
    return fetch_locales_for("region", **rkwargs(request))

@pytest.fixture(scope="function")
def country_src(request):
    return fetch_locales_for("country", **rkwargs(request))

@pytest.fixture(scope="function")
def constituency_src(request):
    return fetch_locales_for("constituency", **rkwargs(request))

@pytest.fixture(scope="function")
def petition():
    return {
        "petition_id": 999999,
        "state": "open",
        "archived": False
    }