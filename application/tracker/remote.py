from flask import current_app
from application.models import Setting
from application.decorators import with_logging

from requests.adapters import HTTPAdapter
from requests.packages import urllib3
from urllib3.util.retry import Retry
from requests_futures.sessions import FuturesSession
from requests import Session as StandardSession
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs

import requests
import json
import itertools
import time, datetime
from datetime import datetime as dt

class SessionMaker():

    @classmethod
    def make(cls, future=False, retries=3, backoff=3, timeout=5, max_workers=24):
        retry_conf = Retry(
            total=retries,
            status_forcelist=[412, 413, 429, 500, 502, 503, 504],
            backoff_factor=backoff,
            method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        if future:
            executor = ThreadPoolExecutor(max_workers=max_workers)
            session = FuturesSession()
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


    base_url = "https://petition.parliament.uk/petitions"
    base_archive_url = "https://petition.parliament.uk/archived/petitions"
    future_session = SessionMaker.make(future=True, retries=1, backoff=1, timeout=1)
    standard_session = SessionMaker.make(future=False, retries=5, backoff=2, timeout=3)

    list_states = [
        'rejected',
        'closed',
        'open',
        'debated',
        'not_debated',
        'awaiting_response',
        'with_response',
        'awaiting_debate',
        'all'
    ]

    petition_states = ["closed", "rejected", "open"]

    @classmethod
    def url_addr(cls, id):
        return cls.base_url + '/' + str(id) + '.json'

    @classmethod
    def page_url_template(cls, state):
        return cls.base_url + ".json?" + '&'.join(["page=%(page)s", "state={}".format(state)])

    @classmethod
    def validate_state(cls, state):
        if not state in cls.list_states:
            error_template = "Invalid state param: '{}', valid states: {}"
            raise ValueError(error_template.format(state, cls.list_states))

    @classmethod
    def page_ints(cls, links):
        get_val = lambda url, key: parse_qs(urlparse(url).query).get(key)
        parse_link = lambda url: int(get_val(url, 'page')[0]) if (url and 'page' in url) else None
        return {k: parse_link(v) for k, v in links.items()}

    # fetch a remote petition by id optionally raise on 404
    @classmethod
    def fetch(cls, logger, id, raise_404=False, **kwargs):
        url = cls.url_addr(id)

        logger.debug("fetching petition ID: {}".format(id))
        response = standard_session.get(url)
        response.timestamp = dt.now().isoformat()

        if (response.status_code == 200):
            response.data = response.json()
            return response
        elif (response.status_code == 404):
            if not raise_404:
                logger.error("could not find petition ID: {}".format(id))
                return None
        else:
            response.raise_for_status()

    @classmethod
    def handle_async_responses(cls, futures):
        results = {}
        results['failed'] = []
        results['success'] = []
        
        for f in futures:
            response = f.result()
            if response.success:
                results['success'].append(response)
            else:
                results['failed'].append(response)

        return results

    @classmethod
    @with_logging()
    def async_poll(cls, logger, petitions, max_retries=0, backoff=3, **kwargs):

        futures = [
            cls.future_session.get(
                url=cls.url_addr(p.id),
                hooks={"response": cls.async_petition_callback(petition=p, id=p.id, logger=logger)})
                for p in petitions
            ]

        results = cls.handle_async_responses(futures)
        results["success"] = results["success"] + kwargs.get("successful", [])
        retries = kwargs.get("retries", 0)
        
        if (retries > 0 and results['failed']):
            petitions = [r.petition for r in results['failed']]
            retry_kwargs = {"retries": retries + 1, "max_retries": max_retries, "backoff": backoff ** retries}
            logger.error("Retrying async poll for: '{}' petitions".format(len(petitions)))
            time.sleep(backoff)
            cls.async_poll(logger=logger, petitions=petitions, successful=results["success"], **retry_kwargs)
        
        success, fail = results["success"], results["failed"]
        logger.info("async poll completed. (Success: '{}', Fail: '{}')".format(len(success), len(fail)))

        return results

    @classmethod
    @with_logging()
    def async_fetch(cls, logger, ids, max_retries=0, backoff=3, **kwargs):

        futures = [
            cls.future_session.get(
                url=cls.url_addr(id),
                hooks={"response": cls.async_petition_callback(id=id, logger=logger)})
                for id in ids
            ]
        
        results = cls.handle_async_responses(futures)
        results["success"] = results["success"] + kwargs.get("successful", [])
        retries = kwargs.get("retries", 0)
        
        if ((retries >= max_retries) and results["failed"]):
            ids = [r.petition_id for r in results['failed']]
            retry_kwargs = {"retries": retries + 1, "max_retries": max_retries, "backoff": backoff ** retries}
            logger.error("Retrying async fetch for ids: '{}'".format(ids))
            time.sleep(backoff)
            cls.async_fetch(logger=logger, ids=ids, successful=results["success"], **retry_kwargs)
        
        success, fail = results["success"], results["failed"]
        logger.info("async fetch completed. (Success: '{}', Fail: '{}')".format(len(success), len(fail)))

        return results

    @classmethod
    def async_petition_callback(cls, **fkwargs):
        def response_hook(response, *args, **kwargs):
            response.id = fkwargs["id"]
            response.petition = fkwargs.get("petition")

            if response.status_code == 200:
                response.data = response.json()
                response.data["archived"] = (response.data['data']['type'] == 'archived-petition')
                response.data["timestamp"] = dt.now().isoformat()
                if response.petition:
                    response.petition.latest_data = response.data
                print("async fetched Petition ID: {}".format(response.id))
                response.success = True
            else:
                error_template = "HTTP error {}, while async fetching ID: {}"
                print(error_template.format(response.status_code, response.id))
                response.success = False

        return response_hook

    @classmethod
    @with_logging()
    def async_query(cls, logger, indexes=[], state='all', max_retries=0, backoff=3, **kwargs):
        if not any(indexes):
            cls.validate_state(state)
            kwargs.update(cls.setup_query(logger=logger, state=state))
            template_url, indexes = kwargs["template_url"], kwargs["indexes"]

        logger.info("executing async query for indexes: {}".format(indexes))
        futures = [
            cls.future_session.get(
                url=(template_url % {"page": i}),
                hooks={"response": cls.async_query_callback(index=i)}
            )
            for i in indexes
        ]

        results = cls.handle_async_responses(futures)
        results["success"] = results["success"] + kwargs.get("successful", [])
        retries = kwargs.get("retries", 0)

        if ((retries >= max_retries) and results["failed"]):
            params["indexes"] = [r.index for r in results["failed"]]
            retry_kwargs = {"retries": retries + 1, "max_retries": max_retries, "backoff": backoff ** retries}
            logger.error("Retrying async query (%(retries)s}/%(max_retries)s). Failed: %(indexes)s" % kwargs)
            time.sleep(backoff)
            cls.async_query(logger=logger,  successful=results["success"], **retry_kwargs, **kwargs)
        
        if any(results["success"]):
            results["success"] = [item for page in results["success"] for item in page.data]
        
        success, failed = len(results["success"]), len(results["failed"])
        logger.info("async query completed, pages failed: '{}', items returned: {}".format(success, failed))

        return results

    
    @classmethod
    def async_query_callback(cls, **fkwargs):
        def response_hook(response, *args, **kwargs):
            if response.status_code == 200:
                response.data = response.json()["data"]
                response.index = fkwargs["index"]
                response.success = True
                print("aync fetched page: {}".format(fkwargs["index"]))
            else:
                response.success = False
                error_template = "HTTP error {}, when async fetching page: {}"
                print(error_template.format(response.status_code, response.index))
            
        return response_hook

    @classmethod
    @with_logging()
    def setup_query(cls, logger, state):
        template_url = cls.page_url_template(state)
        indexes = cls.get_page_range(logger=logger, template_url=template_url)
        return {"template_url": template_url, "indexes": indexes, "state": state}
    
    @classmethod
    @with_logging()
    def get_page_range(cls, logger, template_url, **kwargs):
        logger.info("fetching page indexes")
        response = cls.standard_session.get(template_url % {"page": 1} )
        response.raise_for_status()
        
        first_page = response.json()
        if first_page['links']['next']:
            page_ints = cls.page_ints(first_page["links"])
            return list(range(page_ints['next'], page_ints['last'] + 1))
        else:
            return [1]