import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from flask import Flask
# from flask_oidc import OpenIDConnect
from test_auth_app.backend.config import *
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from test_auth_app.core.worker_manager import WorkerManager

test_auth_app_flask = Flask(__name__, static_folder='../frontend', template_folder='../frontend/templates')
test_auth_app_manager = WorkerManager(number_of_processors=2)

test_auth_app_login = LoginManager(test_auth_app_flask)

# oidc = OpenIDConnect(test_auth_app_flask)

# config = DevelopmentConfig()
config = ProductionConfig()
test_auth_app_flask.config.from_object('test_auth_app.backend.config.ProductionConfig')
test_auth_app_db = SQLAlchemy(test_auth_app_flask)
migrate = Migrate(test_auth_app_flask, test_auth_app_db)

if test_auth_app_flask.config['DEBUG']:
    print('** root_data_dirname = {0}'.format(test_auth_app_flask.config['DIR_DATA']))

from test_auth_app.backend import api
from test_auth_app.backend import db_models
