import faker, factory
from munch import Munch as ObjDict
from datetime import datetime as dt
from datetime import timedelta
from copy import deepcopy
from unittest.mock import MagicMock, PropertyMock, create_autospec
import json, datetime, logging, requests
from application.tests.conftest import init_faker
from application.tests import FROZEN_DATETIME, FROZEN_TIME_STR
from urllib.parse import urlparse, parse_qs

from application.tests.tracker.conftest import geography_keys
from application.tests.tracker.factories.petition import PetitionFactory
from application.tests.tracker.conftest import (
    rand_range_or_int,
    get_geo_key,
    fetch_locales_for,
    rand_percent_locales,
    geography_names,
    geography_keys,
    uk_locale
)

logger = logging.getLogger(__name__)



class QueryFactory():

    fake = init_faker()
    petition_factory = PetitionFactory

    @property
    def __list__(self):
        return getattr(self, "pages", [])

    def __init__(self, state="open", num_pages=1, items_per_page=50, archived=False, imports=None, **kwargs):
        self.state = state
        self.archived = archived
        self.items_per_page = items_per_page
        if imports:
            self.pages = self.load_query(imports)
        else:
            self.pages = self.init_query(num_pages, **kwargs)

    def load_query(self, imports):
        self.imports = imports
        self.preload_check()
        self.paginated = list(self.yield_pages(self.imports, self.items_per_page))
        self.page_range = range(len(self.paginated))
        self.num_pages = len(self.page_range)
        self.base_links = self.init_links()
        return [{"data": page} for page in self.paginated]

    def yield_pages(self, imports, items_per_page):
        for i in range(0, len(imports), items_per_page):
            yield imports[i:i + items_per_page]

    def preload_check(self):
        petition_type = "archived-petition" if self.archived else "petition"
        for petition in self.imports:
            if petition.data.attributes.state != self.state:
                raise ValueError(f"expected imported petition states to be: {self.state}")
            if petition.data.type != petition_type:
                raise ValueError(f"expected imported petition types to be: {petition_type}")

    def init_query(self, num_pages, archived=False, starting_id=0, **kwargs):
        self.page_range = range(num_pages)
        self.num_pages = len(self.page_range)
        self.base_links = self.init_links()
        self.sig_range = kwargs.get("signature_range", range(100, 500_000))
        self.current_id = kwargs.get("starting_id", 0)
        return [self.init_page() for index in self.page_range]

    def init_page(self):
        kwargs = {
            "state": self.state,
            "archived": self.archived,
            "signature_count": self.sig_range
        }

        data = []
        for item in range(self.items_per_page):
            self.current_id += 1
            petition = self.petition_factory(petition_id=self.current_id, **kwargs)
            data.append(petition)

        return {"data": data}

    def init_links(self):
        self.base_url = "https://petition.parliament.uk"
        self.base_url += "/archived/petitions" if self.archived else "/petitions"
        self.link_template = f"{self.base_url}.json?page=%(page)s&state={self.state}"
        self.first_link = f"{self.base_url}.json?state={self.state}"
        self.last_link = self.link_template % {"page": len(self.page_range)}
        return {"first": self.first_link, "last": self.last_link, "prev": None, "next": None}

    def parse_index(self, url):
        get_val = lambda url, key: (parse_qs(urlparse(url).query).get(key) or [None])[0]
        if not url.startswith(self.base_url) or get_val(url, "state") != self.state:
            raise ValueError("url does not match")

        return int(get_val(url, "page")) if "page" in url else 1

    def make_links(self, index=None, url=None):
        links = self.base_links.copy()
        links["self"] = url or self.link_template % {"page": index}
        final_page, is_first_page = self.num_pages, (index in [0, 1])

        if not is_first_page:
            links["prev"] = self.link_template % {"page": index - 1}

        if is_first_page:
            links["next"] = self.link_template % {"page": 2}
        elif index < final_page:
            links["next"] = self.link_template % {"page": index + 1}

        return links

    def make_response(self, data, url):
        response = requests.Response()
        response.status_code = 200
        response.url = url
        response.json = MagicMock(return_value=deepcopy(data))
        response.result = MagicMock(return_value=response)
        return response

    def get(self, url, **kwargs):
        return self.make_response(data=self.get_page(url), url=url)

    # indexes 0 and 1 return first page
    def get_page(self, url=None, index=None):
        if url:
            as_response = True
            index = self.parse_index(url)

        if index < 0 or index > self.num_pages:
            raise ValueError(f"index out of bounds: ({index})/{self.num_pages}")

        pages = deepcopy(self.pages)
        pages.insert(0, pages[0])
        page = pages[index]
        page["data"] = [item.as_query for item in page["data"]]
        return dict(**page, links=self.make_links(index, url))


