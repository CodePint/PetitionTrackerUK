import requests, json

class RemotePetition():

    base_url = "https://petition.parliament.uk/petitions"

    remote_states = [
        'rejected',
        'closed',
        'open',
        'debated',
        'not_debated',
        'awaiting_response',
        'with_response',
        'awaiting_debate',
    ]

    @classmethod
    def fetch_list(cls, index=0, state="all"):
        valid_states = cls.remote_states + list(state)
        if not state in valid_states:
            raise ValueError("Invalid state param, valids states: {}".format(valid_states))
    
        url = cls.base_url + ".json?"
        params = "page={}".format(state) + "&state={}".format(state)
        return  requests.get(url + params)

    @classmethod
    def fetch(cls, id):
        url = cls.base_url + '/' + id + '.json'
        return requests.get(url)
