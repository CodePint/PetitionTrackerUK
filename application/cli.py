from flask import Flask
import subprocess, click, os
from application import context

def register_cli(app, db, celery):
    cli = CliFunction(app, db, celery)
    
    @app.cli.command("init-settings")
    def cli_init_settings():
        print("configuring default values for settings table")
        app.settings.configure(app.config["DEFAULT_SETTINGS"])

    @app.cli.command("init-tasks")
    def cli_init_tasks():
        print("configuring values for periodic tasks")
        app.models.Task.init_tasks(app.config["PERIODIC_TASK_SETTINGS"])

    @app.cli.command("re-init")
    def cli_reinit():
        print("initializing enviroment variables")
        return True

    @app.cli.command("run-tracker-tasks")
    def cli_run_overdue_tasks():
        print("checking for overdue tracker tasks")
        app.celery_utils.run_tasks_for(queue="tracker")
    
    @app.cli.command("react")
    def cli_run_yarn():
        print("starting react frontend")
        subprocess.run("cd frontend && yarn run start", shell=True)

    @app.cli.command("update-geographies")
    def cli_update_geography_data():
        print("updating geography application choices")
        from application.tracker import geographies
        
    @app.cli.command("db-check")
    def cli_check_db():
        print("checking tables")
        cli.check_tables()

    @app.cli.command("db-create")
    def cli_create_db():
        print("creating database!")
        db.create_all()

    @app.cli.command("db-drop")
    def cli_drop_db():
        cli.drop_tables()
        cli.drop_alembic()
        print("database drop completed")

    @app.cli.command("db-drop-alembic")
    def cli_reset_alembic():
        cli.drop_alembic()
    
    @app.cli.command("delete-records")
    def cli_delete_records():
        cli.delete_all_from("Record")
        
    @app.cli.command("delete-petitions")
    def cli_delete_records():
        cli.delete_all_from("Petition")
    
    @app.cli.command("delete-signatures")
    def cli_delete_records():
        cli.delete_all_from("SignaturesByCountry")
        cli.delete_all_from("SignaturesByRegion")
        cli.delete_all_from("SignaturesByConstituency")

    @app.cli.command("purge-celery")
    def cli_purge_celery():
        print("purging celery!")
        app.celery.control.purge()

    @app.cli.command("clear-task-runs")
    def cli_clear_task_runs():
        print("purging tasks!")
        app.models.Task.purge_all()



class CliFunction():

    def __init__(self, app, db, celery):
        self.app = app
        self.db = db
        self.celery = celery

    def drop_alembic(self):
        print("dropping alembic database table!")
        self.db.engine.connect().execute("DROP TABLE IF EXISTS alembic_version")

    def drop_tables(self, models=None):
        print("attempting to dropping tables!")

        with self.app.app_context():
            models = models or context.import_models()
            dropped, failed = [], {}

            for name, model in models.items():
                try:
                    if self.db.engine.has_table(model.__tablename__):
                        model.__table__.drop(self.db.engine)
                        dropped.append(name)
                    else:
                        print("Table: '{}', does not exist".format(name))
                except Exception as error:
                    print("Exception while dropping: '{}', error: {}".format(name, error))
                    failed[name] = model

            print("Tables dropped: {}".format(dropped))

            if any(failed):
                print("Retying drop_tables for: {}".format(failed.values()))
                self.drop_tables(failed)
            else:
                return dropped

    def check_tables(self):
        with self.app.app_context():
            app_models = context.import_models().items()
            tables = [
                name for name, model in app_models
                if self.app.db.engine.has_table(model.__tablename__)
            ]

            print("Tables ({}/{}) found: {}".format(len(tables), len(app_models), tables))
            return tables

    def delete_all_from(self, name):
        model = context.import_models()[name]
        og_count = model.query.count()
        print("deleting all: {} ({})".format(name, og_count))
        
        try:
            model.query.delete()
        except Exception as error:
            count = model.query.count()
            print("error while deleting, remaining: {}. error: {}".format(count, error))

        self.app.db.session.commit()
        count = model.query.count()
        if count == 0:
            print("delete successful! deleted: {}".format(og_count))
        else:
            print("delete incomplete, remaining: {}".format(count))