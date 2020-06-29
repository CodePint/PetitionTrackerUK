import requests, json, itertools

class RemotePetition():

    base_url = "https://petition.parliament.uk/petitions"

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

    petition_states = [
        "closed",
        "rejected",
        "open"
    ]

    # get a remote petition by id
    # optionally raise on 404
    @classmethod
    def get(cls, id, raise_404=False):
        url = cls.base_url + '/' + str(id) + '.json'
        response = requests.get(url)

        if (response.status_code == 200):
            return response
        elif ((response.status_code == 404) and not raise_404):
            return None
        else:
            response.raise_for_status()

    # fetches the page for a given list of query strings and a state
    # default returns first page, or index can be specificed.
    @classmethod
    def get_page(cls, index=1, query=[], state="all"):
        if not state in cls.list_states:
            raise ValueError("Invalid state param, valids list states: {}".format(cls.list_states))
    
        url = cls.base_url + ".json?"

        params = []
        params.append("page={}".format(index))
        params.append("state={}".format(state))
        if query:
            params.append('q={}'.format('+'.join(query)))

        params = '&'.join(params)
        url = (url + params)

        print("fetching page:{}".format(url))
        response = requests.get(url)
        response.raise_for_status()

        return response

    # query remote petitions by state and query string list
    # default returns a single list of items with optional count param
    # or if paginate == True, returns the pages within page_range
    @classmethod
    def query(cls, paginate=False, count=False, page_range=None, query=[], state='all'):
        if paginate:
            first_page = cls.get_page(query=query, state=state).json()
            if not first_page['links']['next']:
                pages = [first_page]
            else:
                page_range = cls.find_page_range(first_page, page_range, query, state)
                pages = [cls.get_page(index=i, query=query, state=state).json() for i in page_range]
                pages.insert(0, first_page)
            
            return pages
        else:
            petitions = cls.get_items(count, query, state)
            return petitions

    # if page range: check it is valid and return it to query
    # if page range is None: return the full range
    # removes the first page from the range as we already have this from the initial get_page()
    @classmethod
    def find_page_range(cls, page, page_range, query, state):
        final_index = int(page['links']['last'].split("?page=")[1].split("&")[0])

        if page_range and (page_range[0] < 1 or (final_index + 1 > page_range[-1])):
            raise IndexError('pages out of range, range: (1..{})'.format(final_index))
        else:
            page_range = range(1, final_index + 1)
        
        return page_range[1:]
    
    # executes the query with get_page() and collects the items from each page
    # returns the results of the query when co
    @classmethod
    def get_items(cls, count, query, state):
        results = []

        index = 1
        next_page = True
        while next_page:
            page = cls.get_page(index=index, query=query, state=state).json()
            next_page = page['links']['next']
            index += 1

            if not page['data']:
                return results

            for item in page['data']:
                results.append(item)
                if count and len(results) == count:
                    return results

        return results

    # deserialise petition json in preparation for onboarding to db
    # ** might rename to parse/prepare **
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