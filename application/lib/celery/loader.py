import os, json
from pathlib import Path

class TaskLoader():

    def __init__(self):
        self.tasks = TaskLoader.init_tasks()
        self.import_templates()
        self.import_schedule()

    def import_templates(self):
        for mod in self.tasks["templates"].keys():
            source = self.tasks["templates"][mod]
            self.tasks["templates"][mod] = self.load_json(source)

    def import_schedule(self):
        source = self.tasks["schedule"]
        self.tasks["schedule"] = self.load_json(source)

    def load_json(self, source):
        with open(source, 'r') as json_file:
            return json.loads(json_file.read())

    @classmethod
    def get_func(cls, func_name, mod_name):
        module = cls.get_module(mod_name)
        return getattr(module, func_name)

    @classmethod
    def init_tasks(cls):
        sources = {"templates": {}}
        parent_dir = Path(__file__).parent
        sources["schedule"] =  os.path.join(parent_dir, "schedule", "schedule.json")
        sources["templates"]["tracker"] = os.path.join(parent_dir, "templates", "tracker.json")
        sources["templates"]["application"] =  os.path.join(parent_dir, "templates", "application.json")

        return sources

    @classmethod
    def get_module(cls, name):
        import application.tracker.tasks as tracker_tasks
        import application.tasks as application_tasks
        modules = {"tracker": tracker_tasks, "application": application_tasks}

        return modules[name]