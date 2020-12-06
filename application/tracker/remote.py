from flask import current_app as c_app
from application.models import Setting
from functools import wraps
from requests.adapters import HTTPAdapter
from requests.packages import urllib3
from urllib3.util.retry import Retry
from requests_futures.sessions import FuturesSession
from requests import Session as StandardSession
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs
from datetime import datetime as dt

import requests, json, itertools, time, datetime
import logging

logger = logging.getLogger(__name__)

class SessionMaker():

    @classmethod
    def make(cls, future=False, retries=3, backoff=3, timeout=5, max_workers=10):
        retry_conf = Retry(
            total=retries,
            backoff_factor=backoff,
            status_forcelist=[412, 413, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )

        if future:
            executor = ThreadPoolExecutor(max_workers=max_workers)
            session = FuturesSession(executor=executor)
        else:
            session = StandardSession()

        adapter = TimeoutHTTPAdapter(timeout=timeout)
        session.mount(prefix="http://", adapter=adapter)
        session.mount(prefix="https://", adapter=adapter)

        return session

class TimeoutHTTPAdapter(HTTPAdapter):

    SANE_TIMEOUT = 5

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop("timeout", TimeoutHTTPAdapter.SANE_TIMEOUT)
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        kwargs["timeout"] = kwargs.pop("timeout", self.timeout)
        return super().send(request, **kwargs)


class RemotePetition():

    base_url = "https://petition.parliament.uk"
    future_session = SessionMaker.make(future=True, retries=1, backoff=1, timeout=1)
    standard_session = SessionMaker.make(future=False, retries=5, backoff=2, timeout=3)

    query_states = [
        "rejected",
        "closed",
        "open",
        "debated",
        "not_debated",
        "awaiting_response",
        "with_response",
        "awaiting_debate",
        "all"
    ]

    petition_states = ["closed", "rejected", "open"]

    @classmethod
    def get_base_url(cls, archived=False):
        return cls.base_url + ("/archived/petitions" if archived else "/petitions")

    @classmethod
    def url_addr(cls, id, archived=False):
        return f"{cls.get_base_url(archived)}/{id}.json"

    @classmethod
    def page_url_template(cls, state, archived=False):
        params = '&'.join(['page=%(page)s', 'state={}'.format(state)])
        return f"{cls.get_base_url(archived)}.json?{params}"

    @classmethod
    def validate_state(cls, state):
        if not state in cls.query_states:
            raise ValueError(f"Invalid state param: '{state}', valid: {cls.query_states}")

    @classmethod
    def retry_msg(cls, func, failed, retries, max_retries, backoff, **kwargs):
        return f"retrying {func} ({retries}/{max_retries} in {backoff}s, for: {failed}"

    @classmethod
    def find_page_nums(cls, links):
        get_val = lambda url, key: (parse_qs(urlparse(url).query).get(key) or [None])[0]
        return {k: get_val(v, "page") for k, v in links.items()}

    @classmethod
    def handle_async_responses(cls, futures, **kwargs):
        results = {"success": [], "failed": [], "processed": {}}
        for f in futures:
            response = f.result()
            if response.success:
                results["success"].append(response)
            else:
                results["failed"].append(response)

        results["processed"]["success"] = len(results["success"])
        results["processed"]["failed"] = len(results["failed"])
        return results

    @classmethod
    def setup_async_retry(cls, results, max_retries, backoff, retries, **kwargs):
        will_retry = (retries >= max_retries) and results["failed"]
        if will_retry:
            kwargs["completed"] = results["success"]
            kwargs["backoff"] = backoff ** retries
            kwargs["max_retries"] = max_retries
            kwargs["retries"] += 1
            return kwargs

        return False

    @classmethod
    def async_callback(cls, obj, func, *args, **kwargs):
        def response_hook(response, *args, **kwargs):
            key, val = list(obj.keys())[0], list(obj.values())[0]
            print(f"executed {func} with {key}: {val}, status: {response.status_code}")

            setattr(response, key, val)
            if response.status_code == 200:
                response.success = True
                response.data = response.json()
                response.timestamp = dt.now().isoformat()
            else:
                response.success = False

        return response_hook

    # poll existing petitions or fetch new ones
    @classmethod
    def async_get(cls, petitions, max_retries=0, backoff=3, retries=0, **kwargs):
        logger.info(f"executing async get for petitions: {petitions}")
        futures = [
            cls.future_session.get(
                url=cls.url_addr(p) if type(p) is int else p.url,
                hooks={"response": cls.async_callback(func="async_get", obj={"petition": p})}
            )
            for p in petitions
        ]

        results = cls.handle_async_responses(futures)
        results["success"] = results["success"] + kwargs.get("completed", [])
        retrying = cls.setup_async_retry(results, max_retries, backoff, retries, **kwargs)

        if retrying:
            failed = [r.petition for r in results["failed"]]
            logger.error(cls.retry_msg("async_get", failed, **retrying))
            time.sleep(backoff)
            cls.async_poll(petitions=failed, **retrying)

        logger.info(f"async get complete, {results['processed']}")
        return results

# Petition.populate()

    # query pages of petitions by state
    @classmethod
    def async_query(cls, indexes=range(0), state="open", max_retries=0, backoff=3, retries=0, **kwargs):
        cls.validate_state(state)
        template_url = cls.page_url_template(state)
        indexes = indexes or cls.get_page_range(template_url)
        logger.info(f"executing async query for indexes: {indexes}")

        futures = [
            cls.future_session.get(
                url=(template_url % {"page": i}),
                hooks={"response": cls.async_callback(func="async_query", obj={"index": i})}
            )
            for i in indexes
        ]

        results = cls.handle_async_responses(futures)
        results["success"] = results["success"] + kwargs.get("completed", [])
        retrying = cls.setup_async_retry(results, max_retries, backoff, retries, **kwargs)

        if retrying:
            failed = [r.index for r in results["failed"]]
            logger.error(cls.retry_msg("async_query", failed, **retrying))
            time.sleep(backoff)
            cls.async_query(indexes=failed, **retrying)

        if results["success"]:
            results["success"] = [item for page in results["success"] for item in page.data["data"]]

        logger.info(f"async query completed, {results['processed']}")
        return results

    @classmethod
    def get_page_range(cls, template_url, **kwargs):
        response = cls.standard_session.get(template_url % {"page": 1} )
        response.raise_for_status()

        first_page = response.json()
        if not first_page["links"]["next"]:
            return [1]

        page_nums = cls.find_page_nums(first_page["links"])
        return list(range(int(page_nums["next"]), int(page_nums["last"]) + 1))

    # fetch a remote petition by id optionally raise on 404
    @classmethod
    def fetch(cls, id, raise_404=False, **kwargs):
        url = cls.url_addr(id)
        logger.debug("fetching petition ID: {}".format(id))
        response = cls.standard_session.get(url)

        if (response.status_code == 200):
            response.timestamp = dt.now().isoformat()
            response.data = response.json()
            return response
        elif (response.status_code == 404):
            if not raise_404:
                logger.error("could not find petition ID: {}".format(id))
                return None

        response.raise_for_status()