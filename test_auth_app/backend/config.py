import os

base_data_dirname = os.path.abspath(os.path.dirname(__file__))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR_NAME = '../frontend/data/'


class Config(object):
    DEBUG = True
    TESTING = False
    SECRET_KEY = 'k4nt<p:Vv8;8nZ>B7G85<agJ=zQrjzPs'
    DIR_BASE = BASE_DIR
    DIR_DATA = os.path.join(BASE_DIR, DATA_DIR_NAME)

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'test_auth_app_flask.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
