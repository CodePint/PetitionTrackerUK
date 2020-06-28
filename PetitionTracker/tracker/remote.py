import requests, json

class Remote():

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

    @classmethod
    def deserialize(cls, petition):
        params = {}
        params['id'] = petition['data']['id']
        params['url'] = petition['links']['self'].split(".json")[0]

        attributes = petition['data']['attributes']
        params['state'] = attributes['state']
        params['action'] = attributes['action']
        params['signatures'] = attributes['signature_count']
        params['background'] = attributes['background']
        params['additional_details'] = attributes['additional_details']
        params['pt_created_at'] = attributes['created_at']
        params['pt_updated_at'] = attributes['updated_at']
        params['pt_rejected_at'] = attributes['rejected_at']
        params['initial_data'] = petition
        params['latest_data'] = petition

        return params

