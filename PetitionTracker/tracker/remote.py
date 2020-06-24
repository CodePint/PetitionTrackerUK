import requests, json

class RemotePetition():

    base_url = "https://petition.parliament.uk/petitions"

    states = [
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
    def list_states(cls):
        return cls.states + ['all']

    @classmethod
    def fetch_list(cls, index=0, state="all"):
        valid_states = cls.list_states()
        if not state in valid_states:
            raise ValueError("Invalid state param, valids states: {}".format(valid_states))
    
        url = cls.base_url + ".json?"
        params = "page={}".format(index) + "&state={}".format(state)
        return  requests.get(url + params)

    @classmethod
    def fetch(cls, id):
        url = cls.base_url + '/' + id + '.json'
        return requests.get(url)
