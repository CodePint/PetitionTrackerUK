import pytest
from copy import deepcopy

def make_links(self_num=False, next_num=False, prev_num=False, last_num=False, state="open"):
    template = "https://petition.parliament.uk/petitions.json?page={}&state="
    make_template = lambda num: template.format(num) + state if num else None
    return {
        "first": "https://petition.parliament.uk/petitions.json?state=open",
        "self": make_template(self_num),
        "last": make_template(last_num),
        "next": make_template(next_num),
        "prev": make_template(prev_num)
    }