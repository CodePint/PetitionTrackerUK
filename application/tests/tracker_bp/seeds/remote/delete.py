import glob, os, logging

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

class DeleteSeeds():

    def __init__(self, state):
        logger.info(f"deleting seed files for {state}")
        self.state = state
        self.configure_paths()
        self.delete_query()
        self.delete_petitions()
        logger.info("seed file deletion completed")
        logger.info(f"petition seed files deleted: {self.petition_files}")

    @classmethod
    def execute(cls, *states):
        logger.info(f"deleting petition seeds, for states: {states}")
        return [DeleteSeeds(s) for s in states]

    def configure_paths(self):
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.query_base_path = os.path.join(self.path, "queries")
        self.petition_base_path = os.path.join(self.path, "petitions", self.state)

    def delete_query(self):
        try:
            query_file = os.path.join(self.query_base_path, f"{self.state}.json")
            logger.info(f"deleting query file: {query_file}")
            os.remove(query_file)
        except OSError as e:
            logger.info(f"query file not found, skipping")

    def delete_petitions(self):
        logger.info(f"deleting petition files at: {self.petition_base_path}")
        self.petition_files = glob.glob(self.petition_base_path + "/*")
        for f in self.petition_files:
            os.remove(f)

DeleteSeeds.execute("open", "closed")