from flask import (
    render_template,
    redirect,
    url_for,
    jsonify,
    make_response,
    request,
    abort
)
from flask import current_app as c_app
from .models import (
    Petition,
    PetitionSchema,
    PetitionNestedSchema,
    Record,
    RecordSchema,
    RecordNestedSchema,
    SignaturesBySchema,
    SignaturesByCountry,
    SignaturesByCountrySchema,
    SignaturesByRegion,
    SignaturesByRegionSchema,
    SignaturesByConstituency,
    SignaturesByConstituencySchema,
)
from sqlalchemy import or_, and_, func, select
import requests, json, os, datetime, logging

logger = logging.getLogger(__name__)

class ViewUtils():

    @classmethod
    def json_abort(cls, status_code, message="Error"):
        abort(make_response(jsonify(message=message), status_code))

    @classmethod
    def abort_404_if_no_result(cls, petition, result, query):
        if not result:
            template = "No signatures found for petition id: '{}', using query: '{}'"
            cls.json_abort(404, template.format(petition.id, query))

    @classmethod
    def get_petition_or_404(cls, id):
        petition = Petition.query.get(id)
        return petition or cls.json_abort(404, "Petition ID: {}, not found".format(id))

    @classmethod
    def abort_400_if_invalid_geography(cls, geography):
        valid = ["region", "country", "constituency"]
        template = "Invalid geographic type: '{}', Allowed: '{}'"
        if geography not in valid:
            cls.json_abort(400, template.format(geography, valid))

    @classmethod
    def abort_400_or_get_state(cls, state):
        STATE_LOOKUP = c_app.models.Petition.STATE_LOOKUP
        try:
            state = STATE_LOOKUP[state]
            return state
        except KeyError:
            template = "Invalid state: '{}', valid states: '{}'"
            cls.json_abort(400, template.format(state, STATE_LOOKUP.values()))

    @classmethod
    def abort_404_or_get_locale_choice(cls, geography, locale):
        try:
            return c_app.models.Record.locale_choice(geography, locale)
        except KeyError:
            template = "Invalid locale: '{}', for: '{}'"
            cls.json_abort(400, template.format(locale, geography))

    @classmethod
    def build_pagination(cls, page, function, **url_kwargs):
        if not page.items:
            return None
        if (page.curr_num > page.pages):
            cls.json_abort(404, "Page out of range: ({}/{})".format((page.curr_num, page.pages)))

        pagination = {"curr": {}, "prev": {}, "next": {}, "last": {}}
        pagination["last"]["index"] = page.pages
        pagination["curr"]["index"] = page.curr_num
        pagination["prev"]["index"] = page.prev_num
        pagination["next"]["index"] = page.next_num

        pagination["curr"]["url"] = url_for(function, index=page.curr_num, **url_kwargs)
        pagination["last"]["url"] = url_for(function, index=page.pages, **url_kwargs)

        pagination["prev"]["url"] = url_for(function, index=page.prev_num, **url_kwargs) \
            if page.has_prev else None
        pagination["next"]["url"] = url_for(function, index=page.next_num, **url_kwargs) \
            if page.has_next else None

        return pagination

    @classmethod
    def items_for(cls, page):
        meta = {}
        meta["total"] = page.total
        meta["on_page"] = len(page.items)
        meta["per_page"] = page.per_page
        return meta

    @classmethod
    def record_timestamp_query(cls, petition, since=None, between=None, geographic=True):
        if since:
            return petition.query_records_since(since, geographic=geographic)
        elif between:
            return petition.query_records_between(lt=between["lt"], gt=between["gt"], geographic=geographic)
        else:
            return petition.ordered_records(geographic=geographic)

    @classmethod
    def order_petitions_by(cls, query, key, by):
        if not key in ["date", "signatures"]:
            return query
        if key == "date":
            key = "pt_created_at"

        model_attr = getattr(c_app.models.Petition, key)
        order_by = getattr(model_attr, by.lower())
        return query.order_by(order_by())

    @classmethod
    def build_base_params(cls, request):
        params = {}
        params['items'] = request.args.get('items', type=int)
        params['since'] = request.args.get('since', type=json.loads)
        params['between'] = request.args.get('between', type=json.loads)
        return params

    @classmethod
    def build_get_petitions_params(cls, request):
        params = {}
        params['items'] = request.args.get('items', type=int)
        params['order_by'] = request.args.get("order_by", type=json.loads)
        params['state'] = request.args.get("state", "all")
        params['action'] = request.args.get("action")
        return params

    @classmethod
    def build_get_petitions_query(cls, params):
        query = Petition.query
        if not params["state"] == "all":
            state = cls.abort_400_or_get_state(params["state"])
            query = Petition.query.filter_by(state=state, archived=False)
        if params["action"]:
            match_filter = Petition.action.match(params["action"], postgresql_regconfig="english")
            query = query.filter(match_filter)
        if params["order_by"]:
            ordering_key = list(params["order_by"])[0]
            ordering_by = params["order_by"][ordering_key]
            query = cls.order_petitions_by(query, ordering_key, ordering_by)

        return query

    @classmethod
    def get_record_for_petition(cls, petition, time_arg):
        if time_arg:
            record = petition.get_closest_record(time_arg)
        else:
            record = petition.latest_record()

        record_schema = RecordNestedSchema(exclude=["id", "petition"])
        return record_schema.dump(record) if record else record


    @classmethod
    def build_signatures_by_locale_query(cls, petition, sig_attrs, locale, params):
        geography = params["geography"]
        query = cls.record_timestamp_query(petition, params["since"], params["between"])
        return query.filter(
            sig_attrs[geography]["relationship"].any(
                sig_attrs[geography]["model"].code == locale["code"]
            )
        )

    @classmethod
    def build_signatures_by_locale(cls, records, sig_schema, sig_attrs, params):
        geography, locale = params["geography"], params["locale"]['code']
        record_schema = RecordSchema(exclude=["id"])

        signatures = []
        for rec in records:
            record_dump = record_schema.dump(rec)
            sig_by = rec.signatures_for(geography, locale)
            record_dump[sig_attrs[geography]["name"]] = sig_schema.dump(sig_by)
            signatures.append(record_dump)

        return signatures

    @classmethod
    def build_signatures_by_geography(cls, records, sig_schema, params):
        geography = params["geography"]
        name = "SignaturesBy{}".format(geography.capitalize())
        record_schema = RecordSchema(exclude=["id"])

        signatures = []
        for rec in records:
            record_dump = record_schema.dump(rec)
            signatures_by = getattr(rec, "by_" + geography)
            record_dump[name] = sig_schema.dump(signatures_by)
            signatures.append(record_dump)

        return signatures

    @classmethod
    def get_total_signatures_and_latest_data(cls, records, latest_record):
        single_record_schema = RecordSchema(exclude=["id"])
        many_record_schema = RecordSchema(many=True, exclude=["id"])
        latest_data = single_record_schema.dump(latest_record)
        signatures = many_record_schema.dump(records)

        return {"latest_data": latest_data, "signatures": signatures}