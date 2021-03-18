import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

__author__ = "eduard.snezhko@gmail.com"

from test_auth_app.backend import test_auth_app_db
from test_auth_app.backend.db_models import User, Role, Application
from test_auth_app.backend.db_models import get_default_roles
from uuid import uuid1


def clear_database():
    users = User.query.all()
    for u in users:
        test_auth_app_db.session.delete(u)
    roles = Role.query.all()
    for r in roles:
        test_auth_app_db.session.delete(r)
    apps = Application.query.all()
    for a in apps:
        test_auth_app_db.session.delete(a)
    test_auth_app_db.session.commit()


def list_users():
    users = User.query.all()
    for u in users:
        print('\n{}:\n\t{}\n\t{}\n{}\n{}\n{}\nvalid = {}'.format(u.id, u.email, u.user_uid, u.roles, u.applications, u.password_hash, u.validated))


def list_roles():
    roles = Role.query.all()
    for r in roles:
        print('{}:\n\t{}\n\t{}\n'.format(r.id, r.role, r.description))


def list_applications():
    apps = Application.query.all()
    for a in apps:
        print('{}:\n\t{}\n\t{}\n'.format(a.id, a.name, a.description))


def init_prod_database():
    user_1 = User(email='empty@email.org', user_uid=str(uuid1()))

    role_read = Role(role='read', description='Can list, view and download cases related to a user')
    role_read_all = Role(role='read_all', description='Can list, view and download all cases related to all user (as admin)')
    role_edit = Role(role='edit', description='Can add new case, run case processing, clear processing results and case delete. Case is relevant to a particular user')
    role_edit_all = Role(role='edit_all', description='Can run case processing, clear processing results and case delete. Case may be relevant to any user (as admin)')

    app_lungs = Application(name='lungs', description='Lungs segmentation on CT images using CNNs')
    app_lesions = Application(name='lesions', description='Lesions segmentation in lungs on CT images using CNNs')

    # Default Anonymous user has access only to the example cases, to list them, preview and download.
    # All apps are available
    user_1.set_password('empty')
    user_1.roles.append(role_read)
    user_1.roles.append(role_edit)
    user_1.set_validated(True)
    user_1.applications.append(app_lungs)
    user_1.applications.append(app_lesions)

    test_auth_app_db.session.add(user_1)
    test_auth_app_db.session.commit()


if __name__ == '__main__':
    # clear_database()
    # init_prod_database()
    # list_users()
    pass
