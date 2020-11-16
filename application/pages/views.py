from flask import render_template, jsonify
from flask import current_app as c_app
from flask import jsonify, make_response, request, abort
from datetime import datetime as dt
import os, logging, requests, json

from application.models import Event, EventSchema
from . import bp

def json_abort(status_code, message="Error"):
    abort(make_response(jsonify(message=message), status_code))

logger = logging.getLogger(__name__)

@bp.route("/ping", methods=["GET"])
def dummy_ping():
    now = dt.now().strftime("%d-%m-%YT%H:%M:%S")
    sender = request.args.get("sender", "N/A")
    logger.info(f"pinged from pages view, by sender: {sender}, at: {now}")
    return {"response": "SUCCESS", "sender": sender, "time": now}

@bp.route("/dummy_event/<name>", methods=["GET"])
def dummy_event(name):
    if not name.startswith("dummy_"):
        json_abort(403, "Only dummy events can be queried from this endpoint")

    event = Event.first(name)
    if not event:
        json_abort(404, f"No events found matching name: {name}")

    event_dump = EventSchema().dump(event)
    logger.info(f"fetched dummy event: {event_dump}")
    return {"event": event_dump}
