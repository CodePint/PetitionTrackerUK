
class Config(object):

    POSTGRES_TEMPLATE = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s'
    POSTGRES_CONFIG = {
        'user': 'petitionadmin',
        'pw': 'new_password',
        'db': 'petitiondb',
        'host': 'localhost',
        'port': '5432',
    }
    
    SQLALCHEMY_DATABASE_URI = POSTGRES_TEMPLATE % POSTGRES_CONFIG
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    DEBUG = True
    # STATIC_FOLDER = 'static'
