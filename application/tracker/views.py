from . import bp
from .utils  import ViewUtils
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

from flask import (
    render_template,
    redirect,
    url_for,
    jsonify,
    current_app,
    request,
    abort
)

from sqlalchemy import or_, and_, func, select
import requests, json, os

# returns a petition with the given id
# optionally returns a geographic/locale breakdown for a given time
@bp.route("/petition/<petition_id>", methods=["GET"])
def get_petition(petition_id):
    time_arg = request.args.get("time")
    get_with_signatures = request.args.get("signatures", type=json.loads)
    petition = ViewUtils.get_petition_or_404(petition_id)

    context = {"petition": PetitionSchema().dump(petition)}
    if petition and get_with_signatures:
        context["signatures"] = ViewUtils.get_record_for_petition(petition, time_arg)

    return context

# returns a list of petitions
@bp.route("/petitions", methods=["GET"])
def get_petitions():
    params = ViewUtils.build_get_petitions_params(request)
    context = {"state": params["state"], "petitions":[]}
    query = ViewUtils.build_get_petitions_query(params)

    context["meta"] = {"query": params}
    if params["items"]:
        blueprint = "tracker_bp.get_petitions"
        index = request.args.get('index', 1, type=int)
        page = query.paginate(index, params["items"], False)
        page.curr_num = index
        total_items = page.total
        petitions = page.items
        context["meta"]["items"] = ViewUtils.items_for(page)
        context["meta"]["pages"] = ViewUtils.build_pagination(page, blueprint, **params)
    else:
        petitions = query.all()
        context["meta"]["items"] = {"total": len(petitions)}

    if petitions:
            petitions_schema = PetitionSchema(many=True)
            context["petitions"] = petitions_schema.dump(petitions)

    return context

# returns timestamped list of total signatures for a petition
@bp.route("/petition/<petition_id>/signatures", methods=["GET"])
def get_petition_signatures(petition_id):
    petition = ViewUtils.get_petition_or_404(petition_id)
    params = ViewUtils.build_base_params(request)
    params["petition_id"] = petition_id

    context = {"petition": PetitionSchema().dump(petition), "signatures": []}
    query = ViewUtils.record_timestamp_query(petition, params["since"], params["between"])

    context["meta"] = {"query": params}
    if params["items"]:
        blueprint = "tracker_bp.get_petition_signatures"
        index = request.args.get('index', 1, type=int)
        page = query.paginate(index, params["items"], False)
        page.curr_num = index
        records = page.items
        context["meta"]["items"] = ViewUtils.items_for(page)
        context["meta"]["links"] = ViewUtils.build_pagination(page, blueprint, **params)
        ViewUtils.abort_404_if_no_result(petition, records, params)
        latest_record = query.first()
    else:
        records = query.all()
        context["meta"]["items"] = {"total": len(records)}
        latest_record = records[0] if any(records) else None

    ViewUtils.abort_404_if_no_result(petition, records, params)
    signatures = ViewUtils.get_total_signatures_and_latest_data(records, latest_record)
    context['meta']['latest_data'] = signatures['latest_data']
    context['signatures'] = signatures['signatures']

    return context

# returns a timestamped geographical list of signatures for a petition
@bp.route("/petition/<petition_id>/signatures_by/<geography>/", methods=["GET"])
def get_petition_signatures_by_geography(petition_id, geography):
    ViewUtils.abort_400_if_invalid_geography(geography)
    petition = ViewUtils.get_petition_or_404(petition_id)
    params = ViewUtils.build_base_params(request)
    params.update({"petition_id": petition_id, "geography": geography})

    context = {"petition": PetitionSchema().dump(petition)}
    query = ViewUtils.record_timestamp_query(petition, params["since"],  params["between"])

    context["meta"] = {"query": params}
    if params["items"]:
        blueprint = "tracker_bp.get_petition_signatures_by_geography"
        index = request.args.get('index', 1, type=int)
        page = query.paginate(index, params["items"], False)
        page.curr_num = index
        context["meta"]["items"] = ViewUtils.items_for(page)
        context["meta"]["links"] = ViewUtils.build_pagination(page, blueprint, **params)
        records = page.items
        latest_record = query.first()
    else:
        records = query.all()
        context["meta"]["items"] = {"total": len(records)}
        latest_record = records[0] if any(records) else None

    ViewUtils.abort_404_if_no_result(petition, records, query)
    sig_exclude = ["id", "record", "timestamp", geography]
    sig_schema = SignaturesBySchema.get_schema_for(geography)(many=True, exclude=sig_exclude)
    latest_data = ViewUtils.build_signatures_by_geography([latest_record], sig_schema, params)
    context["signatures"] = ViewUtils.build_signatures_by_geography(records, sig_schema, params)
    context["meta"]["latest_data"] = latest_data

    return context

# returns timestamped list of signatures for a petition, for a given geographical locale
@bp.route("/petition/<petition_id>/signatures_by/<geography>/<locale>", methods=["GET"])
def get_petition_signatures_by_locale(petition_id, geography, locale):
    ViewUtils.abort_400_if_invalid_geography(geography)
    locale = ViewUtils.abort_404_or_get_locale_choice(geography, locale)
    petition = ViewUtils.get_petition_or_404(petition_id)

    context = {"petition": PetitionSchema().dump(petition)}
    params = ViewUtils.build_base_params(request)
    params.update({"petition_id": petition_id, "geography": geography, "locale": locale})

    index = request.args.get('index', 1, type=int)
    sig_attrs = Record.signature_model_attributes([geography])
    sig_exclude = ["id", "record", "timestamp", geography]
    sig_schema = sig_attrs[geography]["schema_class"](exclude=sig_exclude)
    query = ViewUtils.build_signatures_by_locale_query(petition, sig_attrs, locale, params)

    context["meta"] = {"query": params}
    if params["items"]:
        blueprint = "tracker_bp.get_petition_signatures_by_locale"
        index = request.args.get('index', 1, type=int)
        page = query.paginate(index, params["items"], False)
        page.curr_num = index
        context["meta"]["items"] = ViewUtils.items_for(page)
        context["meta"]["links"] = ViewUtils.build_pagination(page, blueprint, **params)
        records = page.items
        latest_record = query.first()
    else:
        records = query.all()
        context["meta"]["items"] = {"total": len(records)}
        latest_record = records[0] if any(records) else None

    ViewUtils.abort_404_if_no_result(petition, records, params)
    latest_data = latest_record.signatures_by(geography, locale["code"])
    latest_data_schema = sig_attrs[geography]["schema_class"](exclude=[geography])
    context["signatures"] = ViewUtils.build_signatures_by_locale(records, sig_schema, sig_attrs, params)
    context["meta"]["latest_data"] = latest_data_schema.dump(latest_data)

    return context

# compares multiple geographies/locales (slow to execute)
# better to use #get_petition_signatures_by_locale with async requests
@bp.route("/petition/<petition_id>/signatures_by/compare", methods=["POST"])
def get_petition_signatures_comparison(petition_id):
    index = request.args.get("index", 1, type=int)
    items_per_page = request.args.get("items", type=int)
    params = request.json
    params["items_per_page"] = items_per_page
    params["petition_id"] = petition_id

    context = {"signatures": []}
    context["meta"] = {"query": params}
    petition = ViewUtils.get_petition_or_404(petition_id)
    context["petition"]  = PetitionSchema().dump(petition)
    query = ViewUtils.record_timestamp_query(petition, params.get("since"), params.get("between"))

    geographies = params["signatures_by"].keys()
    sig_exclude = ["id", "record", "timestamp"]
    sig_attrs = Record.signature_model_attributes(geographies)

    selects = []
    for geo in geographies:
        sig_attrs[geo]["schema"] = sig_attrs[geo]["schema_class"](exclude=sig_exclude + [geo])
        sig_attrs[geo]["locales"] = [
            Record.get_sig_choice(geo, l)["code"]
            for l in params["signatures_by"][geo]
        ]
        selects.append(
            sig_attrs[geo]["relationship"].any(
            sig_attrs[geo]["model"].code.in_(
            sig_attrs[geo]["locales"]
        )))

    query = query.filter(or_(*selects))

    if items_per_page:
        page = query.paginate(index, items_per_page, False)
        page.curr_num = index
        records = page.items

        context["meta"]["items"] = ViewUtils.items_for(page)
        context["links"] = ViewUtils.build_pagination(
            page,
            "tracker_bp.get_petition_signatures_comparison",
            petition_id=petition_id,
            items=items_per_page
        )
    else:
        records = query.all()
        context["meta"]["items"] = {"total": len(records)}

    ViewUtils.abort_404_if_no_result(petition, records, query)

    record_schema = RecordSchema(exclude=["id"])
    context["signatures"] = [r.signatures_comparison(record_schema, sig_attrs) for r in records]

    return context
