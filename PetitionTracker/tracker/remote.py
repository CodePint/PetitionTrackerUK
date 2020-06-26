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
        'all'
    ]


    @classmethod
    def fetch_list(cls, index=0, state="all"):
        if not state in cls.states:
            raise ValueError("Invalid state param, valids states: {}".format(cls.states))
    
        url = cls.base_url + ".json?"
        params = "page={}".format(index) + "&state={}".format(state)
        response = requests.get(url + params)
        response.raise_for_status()

        return response

    @classmethod
    def fetch(cls, id, raise_404=False):
        url = cls.base_url + '/' + str(id) + '.json'
        response = requests.get(url)

        if (response.status_code == 200):
            return response
        elif ((response.status_code == 404) and not raise_404):
            return None
        else:
            response.raise_for_status()


