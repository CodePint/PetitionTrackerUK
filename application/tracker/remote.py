from flask import current_app as c_app
from functools import wraps
from requests.adapters import HTTPAdapter
from requests.packages import urllib3
from requests_futures.sessions import FuturesSession
from requests import Session as StandardSession
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs
from datetime import datetime as dt
import requests, json, itertools, time, datetime, traceback, logging

def get_traceback(e):
    exc_fmt = dict(etype=type(e), value=e, tb=e.__traceback__)
    return "".join(traceback.format_exception(**exc_fmt))



logger = logging.getLogger(__name__)

class SessionMaker():

    @classmethod
    def make(cls, future=False, timeout=5, max_workers=10):
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
    future_session = SessionMaker.make(future=True, timeout=2)
    standard_session = SessionMaker.make(future=False, timeout=3)

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
    def completed_msg(cls, func, results):
        results = {k: len(v) for k, v in results.items()}
        return f"{func} completed, results: {results}"

    @classmethod
    def find_page_nums(cls, links):
        get_val = lambda url, key: (parse_qs(urlparse(url).query).get(key) or [None])[0]
        return {k: get_val(v, "page") for k, v in links.items()}

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

    @classmethod
    def handle_async_responses(cls, futures):
        results = {"success": [], "failed": []}
        for f in futures:
            response = f.result()
            if response.success:
                results["success"].append(response)
            else:
                results["failed"].append(response)

        return results

    @classmethod
    def eval_async_retry(cls, results, max_retries, backoff, retries):
        setup = {}
        if ((max_retries or 0) > retries) and results["failed"]:
            setup["retries"] = retries + 1
            setup["backoff"] = (backoff or 0) ** setup["retries"]
            setup["max_retries"] = max_retries
            setup["completed"] = results["success"]

        return setup or False

    @classmethod
    def async_callback(cls, func, obj, *args, **kwargs):
        def response_hook(response, *args, **kwargs):
            print(f"executed {func} with {obj}, status: {response.status_code}")
            setattr(response, *list(obj.items())[0])
            response.success = False

            if response.status_code == 200:
                try:
                    response.func = func
                    response.data = response.json()
                    response.timestamp = dt.now().isoformat()
                    response.success = True
                except Exception as e:
                    response.error = get_traceback(e)
                    print(f"error during {func} callback for: {obj}, error: {response.error}")

        return response_hook

    ## async_get + async_query could be simplified in the future
    ## setup the function specific kwargs before execution then call async_exec
    ## object name can be passed via a string and used with getattr/setattr
    ## url could be handled via a lambda kwarg or looked up from a class dict of lambdas

    # poll existing petitions or fetch new ones
    @classmethod
    def async_get(cls, petitions, max_retries=0, backoff=3, retries=0, completed=None):
        logger.info(f"executing async_get for petitions: {petitions}")

        futures = [
            cls.future_session.get(
                url=cls.url_addr(id=p) if type(p) is int else p.url,
                hooks={"response": cls.async_callback(func="async_get", obj={"petition": p})}
            )
            for p in petitions
        ]

        results = cls.handle_async_responses(futures)
        results["success"] += completed or []
        retrying = cls.eval_async_retry(results, max_retries, backoff, retries)

        if retrying:
            failed = [r.petition for r in results["failed"]]
            logger.error(cls.retry_msg("async_get", failed, **retrying))
            time.sleep(backoff)
            return cls.async_get(petitions=failed, **retrying)

        logger.info(cls.completed_msg("async_get", results))
        return results

    # query pages of petitions by state
    @classmethod
    def async_query(cls, indexes=None, state="open", max_retries=0, backoff=3, retries=0, completed=None):
        cls.validate_state(state)
        template_url = cls.page_url_template(state)
        indexes = indexes or cls.get_page_range(template_url)
        logger.info(f"executing async_query for indexes: {indexes}")

        futures = [
            cls.future_session.get(
                url=(template_url % {"page": i}),
                hooks={"response": cls.async_callback(func="async_query", obj={"index": i})}
            )
            for i in indexes
        ]

        results = cls.handle_async_responses(futures)
        results["success"] += completed or []
        retrying = cls.eval_async_retry(results, max_retries, backoff, retries)

        if retrying:
            failed = [r.index for r in results["failed"]]
            logger.error(cls.retry_msg("async_query", failed, **retrying))
            time.sleep(backoff)
            return cls.async_query(indexes=failed, **retrying)

        logger.info(cls.completed_msg("async_query", results))
        return results

    @classmethod
    def get_page_range(cls, template_url):
        response = cls.standard_session.get(template_url % {"page": 1})
        response.raise_for_status()

        first_page = response.json()
        page_nums = cls.find_page_nums(first_page["links"])
        last_page_num = int(page_nums["last"]) if page_nums["next"] else 1
        page_indexes = list(range(1, last_page_num + 1))
        return page_indexes

    @classmethod
    def unpack_query(cls, results):
        return [item for page in results["success"] for item in page.data["data"]]
