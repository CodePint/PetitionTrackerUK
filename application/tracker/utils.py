from flask import (
    render_template,
    redirect,
    url_for,
    jsonify,
    current_app,
    request,
    abort
)

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

import requests, json, os
from sqlalchemy import or_, and_
from datetime import datetime as dt

class ViewUtils():

    @classmethod
    def get_app(cls):
        return current_app._get_current_object()


    @classmethod
    def get_pagination_urls(cls, page, function, **url_kwargs):
        if not page.items:
            return None 
        if (page.curr_num > page.pages):
            abort(404)

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
        if since:
            return petition.query_records_since(since)
        elif between:
            return petition.query_records_between(**between)
        else:
            return petition.ordered_records()
