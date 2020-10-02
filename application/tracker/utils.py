from flask import (
    render_template,
    redirect,
    url_for,
    jsonify,
    make_response,
    current_app,
    request,
    abort
)
import requests, json, os, datetime

class ViewUtils():

    @classmethod
    def json_abort(cls, status_code, message="Error"):
        abort(make_response(jsonify(message=message), status_code))

    @classmethod
    def get_app(cls):
        return current_app._get_current_object()

    @classmethod
    def abort_404_if_no_result(cls, petition, result, query):
        if not result:
            template = "No signatures found for petition id: '{}', using query: '{}'"
            cls.json_abort(404, template.format(petition.id, query))

    @classmethod
    def abort_400_if_invalid_geography(cls, geography):
        valid = ["region", "country", "constituency"]
        template = "Invalid geographic type: '{}', Allowed: '{}'"
        if geography not in valid:
            cls.json_abort(400, template.format(geography, valid))

    @classmethod
    def abort_400_or_get_state(cls, state):
        STATE_LOOKUP = current_app.models.Petition.STATE_LOOKUP
        try:
            state = STATE_LOOKUP[state]
            return state
        except KeyError:
            template = "Invalid state: '{}', valid states: '{}'"
            cls.json_abort(400, template.format(state, STATE_LOOKUP.values()))

    @classmethod
    def abort_404_or_get_locale_choice(cls, geography, locale):
        try:
            return current_app.models.Record.get_sig_choice(geography, locale)
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

        pagination["curr"]["url"] = url_for(function, index=page.curr_num, **url_kwargs)
        pagination["curr"]["index"] = page.curr_num

        pagination["prev"]["url"] = url_for(function, index=page.prev_num, **url_kwargs) \
            if page.has_prev else None
        pagination["prev"]["index"] = page.prev_num

        pagination["next"]["url"] = url_for(function, index=page.next_num, **url_kwargs) \
            if page.has_next else None
        pagination["next"]["index"] = page.next_num

        pagination["last"]["url"] = url_for(function, index=page.pages, **url_kwargs)
        pagination["last"]["index"] = page.pages

        return pagination

    @classmethod
    def items_for(cls, page):
        meta = {}
        meta["total"] = page.total
        meta["on_page"] = len(page.items)
        meta["per_page"] = page.per_page

        return meta

    @classmethod
    def record_timestamp_query(cls, petition, since=None, between=None):
        if since:
            return petition.query_records_since(since)
        elif between:
            return petition.query_records_between(lt=between["lt"], gt=between["gt"])
        else:
            return petition.ordered_records()

    @classmethod
    def order_petitions_by(cls, query, key, by):
        if not key in ["date", "signatures"]:
            return query
        if key == "date":
            key = "pt_created_at"
        
        model_attr = getattr(current_app.models.Petition, key)
        order_by = getattr(model_attr, by.lower())
        return query.order_by(order_by())
