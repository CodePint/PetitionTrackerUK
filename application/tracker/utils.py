from .models import (
    Petition,
    Record,
    PetitionSchema,
    PetitionNestedSchema,
    RecordSchema,
    RecordNestedSchema,
)
from flask import url_for, jsonify, make_response, request, abort
from json.decoder import JSONDecodeError
from urllib.parse import urlencode
import requests, json, datetime, logging

blueprint = "tracker_bp"
logger = logging.getLogger(__name__)



class ViewUtils():

    REQUEST_WHITELIST = {
        "pagination": ["index", "items"],
        "record": ["timestamp", "order"],
        "petition": ["archived", "text", "expressions", "order_by"],
    }

    @classmethod
    def url_for(cls, func, index, values, **params):
        url = url_for(f"{blueprint}.{func.__name__}", index=index, **values)
        params = urlencode({k: json.dumps(v) for k, v in params.items()})
        return f"{url}&{params}"

    @classmethod
    def abort(cls, status_code, message="Error"):
        abort(make_response(jsonify(message=message), status_code))

    @classmethod
    def parse_params(cls, request, *keys, **params):
        NOT_FOUND = "ARG_NOT_FOUND"
        for k in keys:
            val = request.args.get(k, NOT_FOUND)
            if val != NOT_FOUND:
                try:
                    params[k] = json.loads(val)
                except JSONDecodeError:
                    params[k] = str(val)
                except TypeError:
                    pass
        return params

    @classmethod
    def get_params(cls, request, whitelist, *manual, **merge):
        keys = cls.REQUEST_WHITELIST[whitelist] + list(manual)
        return cls.parse_params(request, *keys, **merge)

    @classmethod
    def handle(cls, context, query, request, func):
        pagination_params = ViewUtils.get_params(request, "pagination")

        params = context["meta"]["query"]
        values = context["meta"]["values"]
        params.update(**pagination_params)
        will_paginate = params.get("items")
        if will_paginate:
            index = params.pop("index", 1)
            page = query.paginate(index, params["items"], False)
            pagination = cls.paginate(index, page, func, values,**params)

            context["meta"].update(pagination)
            result = page.items
        else:
            result = query.all()
            context["meta"]["items"] = {"total": len(result)}

        return result


    @classmethod
    def serialize(cls, context, petition, results, latest, geography=None, locale=None, petition_id=None):
        if not results:
            template = "No matching results found for petition id: {}"
            cls.abort(404, template.format(petition_id))

        if geography:
            exclude = ["id", "record", "timestamp"]
            signatures = RecordSchema.dump_query(results, geography, locale, exclude)
            latest_data = RecordSchema.dump_query(latest, geography, locale, exclude)
        else:
            signatures = RecordSchema(many=True, exclude=["id"]).dump(results)
            latest_data = RecordSchema(exclude=["id"]).dump(latest)

        context["petition"] = PetitionSchema().dump(petition)
        context["signatures"] = signatures
        context["meta"]["latest_data"] = latest_data

    @classmethod
    def get_latest_data(cls, petition, geography=None, locale=None):
        geographic = True if geography else None
        record = petition.record_query(geographic=geographic).first()
        return Record.signatures_query([record], geography, locale).first() if locale else record

    @classmethod
    def paginate(cls, index, page, func, values, **params):
        items = {"total": page.total, "on_page": len(page.items), "per_page": page.per_page}

        if not page.items:
            return {"links": {}, "items": items}

        page.curr_num = index
        page.last_num = page.pages
        if (page.curr_num > page.last_num):
            template = "invalid page index: ({}/{})"
            cls.abort(404, template.format(page.curr_num, page.last_num))

        links = cls.build_links(page, func, values, params)
        return {"links": links, "items": items}

    @classmethod
    def build_links(cls, page, func, values, params):
        has_page = lambda k: getattr(page, f"has_{k}")
        get_index = lambda k: getattr(page, f"{k}_num")

        links = {}
        for key in ["curr", "prev", "next", "last"]:
            index = get_index(key)
            exists = has_page(key) if key in ["prev", "next"] else True
            url = cls.url_for(func, index, values, **params) if exists else None
            links[key] = {"url": url, "index": index}

        return links

    @classmethod
    def get_petition_or_404(cls, petition_id):
        petition = Petition.query.get(petition_id)
        if not petition:
            cls.abort(404, "Petition ID: {}, not found".format(petition_id))

        return petition

    @classmethod
    def get_locale_or_400(cls, geography, locale):
        try:
            return Record.locale_choice(geography, locale)
        except KeyError:
            template = "Invalid locale: '{}', for: '{}'"
            cls.abort(400, template.format(locale, geography))

    @classmethod
    def validate_state_or_400(cls, state):
        try:
            state == "all" or Petition.STATE_LOOKUP[state]
        except KeyError:
            template = "Invalid state: '{}', valid states: '{}'"
            cls.abort(400, template.format(state, Petition.STATE_VALUES))

    @classmethod
    def validate_geography_or_400(cls, geography):
        valid = ["region", "country", "constituency"]
        if geography not in valid:
            template = "Invalid geographic type: '{}', Allowed: '{}'"
            cls.abort(400, template.format(geography, valid))
