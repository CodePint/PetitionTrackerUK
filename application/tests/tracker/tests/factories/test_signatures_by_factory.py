import pytest
from random import randint, randrange
import os, json, logging
from copy import deepcopy
from datetime import timedelta
from datetime import datetime as dt

from application.tests.conftest import get_kwargs
from application.tests.tracker.factories.signatures import SignaturesByFactory
from application.tests.tracker.conftest import (
    geography_names,
    geography_keys,
    copy_geo_src,
    get_geo_key,
    get_code_key,
    invert_dict,
    exclude_locale,
    list_of_counts,
    dict_of_counts,
    uk_locale,
    rand_pop,
    rand_percent_locales,
    rand_range_or_int
)

logger = logging.getLogger(__name__)


class TestSignaturesByFactory():

    predef_templates = [
        {"code": False, "name": True,  "count": range(50, 500)},
        {"code": True, "name": False, "count": range(50, 500)},
        {"code": True, "name": True, "count": 1000},
        {"code": True, "name": True, "count": False},
        {"code": False, "name": True, "count": False},
        {"code": True, "name": False, "count": False},
    ]

    @classmethod
    def make_templates(cls, geo, templates, **kwargs):
        source = copy_geo_src(geo)
        if kwargs.get("exclude_uk") and geo == "country":
            source = exclude_locale(geo, source, uk_locale())

        source = [rand_pop(source) for i in range(len(templates))]
        return [cls.parse_template(geo, tmpl, loc) for tmpl, loc in zip(templates, source)]

    @classmethod
    def parse_template(cls, geo, template, locale):
        if not template.get("name"):
            locale.pop("name")
        if not template.get("code"):
            code_key = get_code_key(geo)
            locale.pop(code_key)
        if template.get("count"):
            locale["count"] = rand_range_or_int(template["count"])

        return locale

    @classmethod
    def verify_values(cls, geo, locations, source):
        code = get_code_key(geo)
        invert_source = invert_dict(source)
        for locale in locations:
            source[locale[code]]
            invert_source[locale["name"]]

        return True

    @classmethod
    def verify_counts(cls, geo, result, predef):
        code_key = get_code_key(geo)
        matches = 0
        for locale in result:
            code, name = locale[code_key], locale["name"]
            predef_count = predef.get(code) or predef.get(name)
            if predef_count:
                assert predef_count == locale["count"]
                matches += 1

        return matches

    @classmethod
    def init_config(cls, geo, sigs, predef, undef):
        return {
            "geography": geo,
            "signatures": sigs,
            "locales": {
                "predef": predef,
                "undef": undef
            }
        }

    @classmethod
    def build_config(cls, locales):
        build_config = {"country": {}, "region": {}, "constituency":  {}}
        for geo, predef in locales.items():
            build_config[geo]["locales"] = {}
            build_config[geo]["locales"]["predef"] = predef
            build_config[geo]["locales"]["undef"] = rand_percent_locales(geo)

        return build_config

    @pytest.fixture(scope="function")
    def predef_locales(self, request):
        kwargs = get_kwargs(request)
        self.predef_locales = {}
        for geo in geography_names():
            templates = self.make_templates(geo, self.predef_templates, **kwargs)
            self.predef_locales[geo] = templates

    def test_init_success(self, geo_src_dict, predef_locales):
        for geo, predef in self.predef_locales.items():
            logger.info(f"testing for: {geo}")

            undef = rand_percent_locales(geo)
            sigs = randint(5_000, 100_000)
            config = self.init_config(geo, sigs, predef, undef)

            locale_source_dict = geo_src_dict[geo]
            predef_with_count = dict_of_counts(geo, predef)
            expected_num_locales = (len(predef) + undef)

            result = SignaturesByFactory(**config).__dict__

            assert self.verify_values(geo, result, locale_source_dict) is True
            assert self.verify_counts(geo, result, predef_with_count) == len(predef_with_count)
            assert len(result) == expected_num_locales
            assert sum(list_of_counts(result)) == sigs

    def test_init_fails_if_predef_count_greater_than_total(self, predef_locales):
        for geo, predef in self.predef_locales.items():
            logger.info(f"testing for: {geo}")
            sigs = randint(1, 50)
            config = self.init_config(geo, sigs, predef, rand_percent_locales(geo))

            expected_error_msg = f"total signatures ({sigs}) less than predef counts"
            with pytest.raises(ValueError) as e:
                result = SignaturesByFactory(**config).__dict__

            assert str(e.value) == expected_error_msg

    def test_init_fails_if_predef_locale_not_found(self, predef_locales):
        for geo, predef in self.predef_locales.items():
            logger.info(f"testing for: {geo}")

            invalid_locale = {get_code_key(geo): "FOO"}
            predef.append(invalid_locale)
            config = self.init_config(geo, randint(5_000, 100_000), predef, rand_percent_locales(geo))

            expected_error_msg = f"invalid locales(s): {[invalid_locale]}"
            with pytest.raises(ValueError) as e:
                result = SignaturesByFactory(**config).__dict__

            assert str(e.value) == expected_error_msg

    @pytest.mark.parametrize('predef_locales', [{"exclude_uk": True}], indirect=True)
    def test_build_successful_with_uk_present(self, predef_locales):
        total_count = 100_000
        national_count = 65_000
        build_config = self.build_config(self.predef_locales)
        UK = dict(**uk_locale(), count=national_count)
        build_config["country"]["locales"]["predef"].append(UK)
        expected_predef_counts = {g: dict_of_counts(g, c["locales"]["predef"]) for g, c in build_config.items()}

        result = SignaturesByFactory.build(**deepcopy(build_config), signatures=total_count).__dict__

        assert sorted(list(result.keys())) == geography_keys()
        assert sum(list_of_counts(result[get_geo_key("country")])) == total_count
        assert sum(list_of_counts(result[get_geo_key("region")])) == national_count
        assert sum(list_of_counts(result[get_geo_key("constituency")])) == national_count

        num_locales = lambda src, key: len(src[key]["locales"]["predef"]) + src[key]["locales"]["undef"]
        assert len(result[get_geo_key("country")]) == num_locales(build_config, "country")
        assert len(result[get_geo_key("region")]) == num_locales(build_config, "region")
        assert len(result[get_geo_key("constituency")]) == num_locales(build_config, "constituency")

        for geo, predef in expected_predef_counts.items():
            verified = self.verify_counts(geo, result[get_geo_key(geo)], predef)
            assert verified == len(predef)

    def test_build_fails_without_uk_present(self, predef_locales):
        total_count = 100_000
        build_config = self.build_config(self.predef_locales)

        expected_msg = "UK not in predefined countries"
        with pytest.raises(ValueError) as e:
            result = SignaturesByFactory.build(**deepcopy(build_config), signatures=total_count)

        assert str(e.value) == expected_msg




