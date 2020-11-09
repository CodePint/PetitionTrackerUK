from flask import Flask
import subprocess, click, os
from application import context

def register(app, db, celery):
    cli_func = CliFunction(app, db, celery)

    task_cli(app, db, celery, cli_func)
    db_cli(app, db, celery, cli_func)
    exec_cli(app, db, celery, cli_func)

    @app.cli.command("--init-settings")
    def init_settings():
        click.echo("configuring default values for settings table")
        app.models.Setting.configure(app.config["DEFAULT_SETTINGS"])

    @app.cli.command("--update-geographies")
    def update_geography_data():
        click.echo("updating geography application choices")
        from application.tracker import geographies



def exec_cli(app, db, celery, cli_func):

    SCRIPTS_DIR = app.config["PROJ_SCRIPTS_DIR"]

    @app.cli.group("exec")
    def exec_group():
        pass

    @exec_group.command()
    def react():
        click.echo("starting react frontend")
        subprocess.run("cd frontend && yarn run start", shell=True)

    @exec_group.command()
    def gunicorn():
        gunicorn = os.path.join(SCRIPTS_DIR, "flask", "wsgi")
        subprocess.run(f"{gunicorn}.sh")

    @exec_group.group("celery")
    def celery_group():
        pass

    @click.option("--name", required=True)
    @celery_group.command("worker")
    def worker(name):
        worker = os.path.join(SCRIPTS_DIR, "celery/workers", name)
        subprocess.run(f"{worker}.sh")

    @celery_group.command()
    def beat():
        beat = os.path.join(SCRIPTS_DIR, "celery", "beat")
        subprocess.run(f"{beat}.sh")

    @celery_group.command()
    def flower():
        flower = os.path.join(SCRIPTS_DIR, "celery", "flower")
        subprocess.run(f"{flower}.sh")



def db_cli(app, db, celery, cli_func):

    @app.cli.group("db-cli")
    def db_cli_group():
        pass

    @db_cli_group.command()
    def check():
        click.echo("checking tables")
        cli_func.check_tables()

    @db_cli_group.command()
    def create():
        click.echo("creating database!")
        db.create_all()

    @db_cli_group.command("drop-all")
    def drop_all():
        cli_func.drop_tables()

    @click.argument("--models", nargs=-1)
    @db_cli_group.command()
    def drop(models):
        cli_func.drop_tables(models)

    @db_cli_group.command("reset-alembic")
    def reset_alembic():
        cli_func.drop_alembic()

    @click.option("--model")
    @db_cli_group.command()
    def delete(model):
        cli_func.delete_all_from(model)



def task_cli(app, db, celery, cli_func):

    @app.cli.group("tasks")
    def tasks_group():
        pass

    @click.option("--schedule/--no-schedule", default=False)
    @click.option("--templates/--no-templates", default=False)
    @tasks_group.command("init")
    def init(schedule, templates):
        if schedule:
            app.celery_utils.init_schedule(overwrite=True)
        if templates:
            app.celery_utils.init_templates(overwrite=True)

    @click.option("--name", required=True)
    @click.option("--key", required=True)
    @tasks_group.command()
    def send(name, key):
        app.celery_utils.send_task(name=name, key=key)

    @click.option("--all-global/--no-all-global", default=False)
    @click.option("--name")
    @click.option("--key")
    @tasks_group.command()
    def revoke(all_global, name, key):
        if all_global:
            click.echo("revoking all tasks!")
            app.models.Task.revoke_all()
        if name and key:
            task = app.models.Task.get(name=name, key=key)
            if task:
                click.echo(f"revoking task: {name}/{key}")
                task.revoke()
            else:
                click.echo(f"task not found: {name}/{key}")



class CliFunction():

    def __init__(self, app, db, celery):
        self.app = app
        self.db = db
        self.celery = celery

    def drop_alembic(self):
        click.echo("dropping alembic database table!")
        self.db.engine.connect().execute("DROP TABLE IF EXISTS alembic_version")

    def drop_tables(self, models=None):
        ("attempting to dropping tables!")

        with self.app.app_context():
            models = models or context.import_models()
            dropped, failed = [], {}

            for name, model in models.items():
                try:
                    if self.db.engine.has_table(model.__tablename__):
                        model.__table__.drop(self.db.engine)
                        dropped.append(name)
                    else:
                        click.echo("Table: '{}', does not exist".format(name))
                except Exception as error:
                    click.echo("Exception while dropping: '{}', error: {}".format(name, error))
                    failed[name] = model

            click.echo("Tables dropped: {}".format(dropped))

            if any(failed):
                click.echo("Retying drop_tables for: {}".format(failed.values()))
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

            click.echo("Tables ({}/{}) found: {}".format(len(tables), len(app_models), tables))
            return tables

    def delete_all_from(self, name):
        model = context.import_models()[name]
        og_count = model.query.count()
        click.echo("deleting all: {} ({})".format(name, og_count))

        try:
            model.query.delete()
        except Exception as error:
            count = model.query.count()
            click.echo("error while deleting, remaining: {}. error: {}".format(count, error))

        self.app.db.session.commit()
        count = model.query.count()
        if count == 0:
            click.echo("delete successful! deleted: {}".format(og_count))
        else:
            click.echo("delete incomplete, remaining: {}".format(count))