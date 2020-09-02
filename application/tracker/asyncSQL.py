from concurrent.futures import ThreadPoolExecutor
import concurrent
from flask import current_app

class AsyncSQL():

    @classmethod
    def get_app(cls):
        pass

    @classmethod
    def async_query(cls, function, iterable, workers=6, **kwargs):
        print("running async query")

        session = current_app.db.create_scoped_session()

        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = {
                executor.submit(
                    getattr(cls, function), cls.get_app(), session, item, **kwargs
                ) for item in iterable
            }

        results = []
        for f in concurrent.futures.as_completed(futures):
            result = f.result()
            results.append(result)
        
        return results

    @classmethod
    def signatures_for_record(cls, app, session, record, record_schema, sig_attrs):
        with app.app_context():
            app.db.session = session
            # app.db.session.add(record)
            print("generating comparison for".format(record.id))
            
            comparison = record_schema.dump(record)
            for geo in sig_attrs.keys():
                name, schema = [sig_attrs[geo]['name'], sig_attrs[geo]['schema']]
                model, relation = record.get_sig_model_relation(geo)
                filtered = relation.filter(model.code.in_(sig_attrs[geo]['locales'])).all()
                comparison[name] = [schema.dump(sig) for sig in filtered]
            
            # app.db.session.remove()
        return comparison


# signatures = AsyncSQL.async_query(
#     function='signatures_for_record',
#     iterable=records,
#     workers=8,
#     record_schema=RecordSchema(exclude=["id"]),
#     sig_attrs=sig_attrs,
# )