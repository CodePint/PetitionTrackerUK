from application.tracker.models import Petition, Record
from application.tracker.models import (
    PetitionSchema,
    RecordSchema,
    RecordNestedSchema,
)

from application.tracker.utils import ViewUtils
from application.tracker import bp
from flask import request, abort
from datetime import datetime as dt
import json, logging

logger = logging.getLogger(__name__)

# get a petition for a given id, optional signature date for given timestamp
@bp.route("/petition/<petition_id>", methods=["GET"])
def get_petition(petition_id):
    petition = ViewUtils.get_petition_or_404(petition_id)
    context = {"petition": PetitionSchema().dump(petition)}
    fetch_signatures = request.args.get("signatures")

    if fetch_signatures:
        timestamp = {"lt": request.args.get("timestamp") or dt.now()}
        record_schema = RecordNestedSchema(exclude=["id", "petition"])
        record = petition.record_query(timestamp=timestamp, geographic=True).first()
        context["signatures"] = record_schema.dump(record) if record else {}

    return context

# get a list of petitions for a given state state and query on action
@bp.route("/petitions", methods=["GET"])
@bp.route("/petitions/<state>", methods=["GET"])
def get_petitions_where(state="all"):
    values = {"state": state}
    ViewUtils.validate_state_or_400(state)

    params = ViewUtils.get_params(request, whitelist="petition")
    query = Petition.where(state=state, **params)
    context = {"meta": {"query": params, "values": values}}

    petitions = ViewUtils.handle(context, query, request, get_petitions_where)
    serialized_petitions = PetitionSchema(many=True).dump(petitions)
    context.update(petitions=serialized_petitions)
    return context

# returns timestamped list of total signatures for a given petition
@bp.route("/petition/<petition_id>/signatures", methods=["GET"])
def get_signature_totals_for(petition_id):
    values = {"petition_id": petition_id}
    petition = ViewUtils.get_petition_or_404(petition_id)

    params = ViewUtils.get_params(request, whitelist="record")
    query = petition.record_query(geographic=None, **params)
    context = {"meta": {"query": params, "values": values}}

    records = ViewUtils.handle(context, query, request, get_petitions_where)
    latest_record = ViewUtils.get_latest_data(petition)
    ViewUtils.serialize(context, petition, records, latest_record, **values)
    return context

# returns a timestamped list of signatures for a given petition/geography
@bp.route("/petition/<petition_id>/signatures_by/<geography>", methods=["GET"])
def get_signatures_by_geography_for(petition_id, geography):
    values = {"petition_id": petition_id, "geography": geography}
    ViewUtils.validate_geography_or_400(geography)
    petition = ViewUtils.get_petition_or_404(petition_id)

    params = ViewUtils.get_params(request, whitelist="record")
    query = petition.record_query(geographic=True, join_on=geography, **params)
    context = {"meta": {"query": params, "values": values}}

    records = ViewUtils.handle(context, query, request, get_signatures_by_geography_for)
    latest_record = ViewUtils.get_latest_data(petition, geography)
    ViewUtils.serialize(context, petition, records, latest_record, **values)
    return context

# returns timestamped list of signatures for a given petition/locale
@bp.route("/petition/<petition_id>/signatures_by/<geography>/<locale>", methods=["GET"])
def get_signatures_by_locale_for(petition_id, geography, locale):
    values = {"petition_id": petition_id, "geography": geography, "locale": locale}
    ViewUtils.validate_geography_or_400(geography)
    locale = ViewUtils.get_locale_or_400(geography, locale)
    petition = ViewUtils.get_petition_or_404(petition_id)

    params = ViewUtils.get_params(request, whitelist="record")
    records = petition.record_query(geographic=True, **params).all()
    query = Record.signatures_query(records, geography, locale, params.get("order"))
    context = {"meta": {"query": params, "values": values, "locale": locale}}

    signatures_by = ViewUtils.handle(context, query, request, get_signatures_by_locale_for)
    latest_signatures_by = ViewUtils.get_latest_data(petition, geography, locale)
    ViewUtils.serialize(context, petition, signatures_by, latest_signatures_by, **values)
    return context

