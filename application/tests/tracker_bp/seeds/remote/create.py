import subprocess, os, json, logging
from application.tracker.remote import RemotePetition as Remote

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

class CreateSeeds():
    def __init__(self, state="open", pages=1):
        self.state = state
        self.indexes = range(1, pages + 1)
        self.configure_paths()

        logger.info(f"fetching petition seeds for state: {self.state}")
        self.query_response = self.fetch_query()
        self.petition_ids = self.ids_from_query()
        self.petition_responses =  self.fetch_petitions()

        self.write_query()
        self.write_petitions()
        logger.info("seed data fetch completed")
        logger.info(f"petition seed files: {self.petition_files}")

    @classmethod
    def execute(cls, *states, pages):
        logger.info(f"fetching {pages} pages of petition seeds, for states: {states}")
        return [CreateSeeds(s, pages) for s in states]

    def fetch_query(self):
        logger.info(f"querying remote for state: {self.state}")
        return Remote.async_query(state=self.state, indexes=self.indexes)

    def fetch_petitions(self):
        logger.info(f"fetching remote petitions: {self.petition_ids}")
        return Remote.async_fetch(self.petition_ids)
        logger.info("petition seed fetch completed")

    def ids_from_query(self):
        return [r["id"] for r in self.query_response["success"]]

    def configure_paths(self):
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.query_base_path = os.path.join(self.path, "queries")
        self.petition_base_path = os.path.join(self.path, "petitions", self.state)
        os.makedirs(self.query_base_path, exist_ok=True )
        os.makedirs(self.petition_base_path, exist_ok=True)

    def write_query(self):
        filename = f"queries/{self.state}"
        logging.info(f"writing query response to: {filename}")
        filepath = os.path.join(self.query_base_path, f"{self.state}.json")
        with open(filepath, "w") as query_file:
            json.dump(self.query_response, query_file, indent=4)

    def write_petitions(self):
        self.petition_files = []
        for response in self.petition_responses["success"]:
            filename = os.path.join(self.petition_base_path, f"{response.id}.json")
            self.petition_files.append(filename)
            logging.info(f"writing petitions response to: {filename}")
            with open(filename, "w") as petition_file:
                json.dump(response.data, petition_file, indent=4)

CreateSeeds.execute("open", "closed", pages=1)
