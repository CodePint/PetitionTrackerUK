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
import requests, json, os
from datetime import datetime as dt


class ViewUtils():

    @classmethod
    def json_abort(cls, status_code, message='Error'):
        abort(make_response(jsonify(message=message), status_code))

    @classmethod
    def get_app(cls):
        return current_app._get_current_object()

    @classmethod
    def abort_404_if_no_result(cls, petition, result, query):
        if not result:
            template = "No signatures found for petition id: {}, using query: {}"
            cls.json_abort(404, template.format(petition.id, query))

    @classmethod
    def abort_400_if_invalid_geography(cls, geography):
        valid = ['region', 'country', 'constituency']
        template = "Invalid geographic type: '{}', Allowed: {}"
        if geography not in valid:
            cls.json_abort(400, template.format(geography, valid))

    @classmethod
    def abort_404_or_get_locale_choice(cls, geography, locale):
        try:
            return current_app.models.Record.get_sig_choice(geography, locale)
        except KeyError:
            template = "Invalid locale: {}, for: {}"
            cls.json_abort(400, template.format(locale, geography))

    @classmethod
    def get_pagination_urls(cls, page, function, **url_kwargs):
        if not page.items:
            return None 
        if (page.curr_num > page.pages):
            cls.json_abort(404, "Page out of range: ({}/{})".format((page.curr_num, page.pages)))

        links = {}
        links['curr_url'] = url_for(function, index=page.curr_num, **url_kwargs)
        links['prev_url'] = url_for(function, index=page.prev_num, **url_kwargs) \
            if page.has_prev else None
        links['next_url'] = url_for(function, index=page.next_num, **url_kwargs) \
            if page.has_next else None
        links['last_url'] = url_for(function, index=page.pages, **url_kwargs)

        return links

    @classmethod
    def items_for(cls, page):
        meta = {}
        meta['total'] = page.total
        meta['on_page'] = len(page.items)
        meta['per_page'] = page.per_page

        return meta

    @classmethod
    def record_timestamp_query(cls, petition, since=None, between=None):
        # breakpoint()
        if since:
            return petition.query_records_since(**since)
        elif between:
            return petition.query_records_between(**between)
        else:
            return petition.ordered_records()
