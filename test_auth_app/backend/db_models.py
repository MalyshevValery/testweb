# User database models

from test_auth_app.backend import test_auth_app_db
from test_auth_app.backend import test_auth_app_login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

user_role = test_auth_app_db.Table('user_role',
                                   test_auth_app_db.Column('user_id', test_auth_app_db.Integer, test_auth_app_db.ForeignKey('user.id'), primary_key=True),
                                   test_auth_app_db.Column('role_id', test_auth_app_db.Integer, test_auth_app_db.ForeignKey('role.id'), primary_key=True))

user_app = test_auth_app_db.Table('user_app',
                                  test_auth_app_db.Column('user_id', test_auth_app_db.Integer, test_auth_app_db.ForeignKey('user.id'), primary_key=True),
                                  test_auth_app_db.Column('app_id', test_auth_app_db.Integer, test_auth_app_db.ForeignKey('application.id'), primary_key=True))


class User(UserMixin, test_auth_app_db.Model):
    id = test_auth_app_db.Column(test_auth_app_db.Integer, primary_key=True)
    user_uid = test_auth_app_db.Column(test_auth_app_db.String(36), index=True, unique=True)
    email = test_auth_app_db.Column(test_auth_app_db.String(128), index=True, unique=True)
    password_hash = test_auth_app_db.Column(test_auth_app_db.String(128))
    validated = test_auth_app_db.Column(test_auth_app_db.Boolean(), unique=False, default=False)
    roles = test_auth_app_db.relationship('Role', secondary=user_role, lazy='subquery',
                                          backref=test_auth_app_db.backref('users', lazy=True))
    applications = test_auth_app_db.relationship('Application', secondary=user_app, lazy='subquery',
                                                 backref=test_auth_app_db.backref('users', lazy=True))

    def __repr__(self):
        return '{}'.format(self.email)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_validated(self, is_validated):
        self.validated = is_validated

    def is_validated(self):
        return self.validated


class Role(test_auth_app_db.Model):
    id = test_auth_app_db.Column(test_auth_app_db.Integer, primary_key=True)
    role = test_auth_app_db.Column(test_auth_app_db.String(16), index=True, unique=True)
    description = test_auth_app_db.Column(test_auth_app_db.String(512))

    def __repr__(self):
        return '{}'.format(self.role)


class Application(test_auth_app_db.Model):
    id = test_auth_app_db.Column(test_auth_app_db.Integer, primary_key=True)
    name = test_auth_app_db.Column(test_auth_app_db.String(16), index=True, unique=True)
    description = test_auth_app_db.Column(test_auth_app_db.String(512))

    def __repr__(self):
        return '{}'.format(self.name)


# Default Roles and Applications

def gen_default_roles():
    role_read = Role(role='read', description='Can list, view and download cases related to a user')
    role_edit = Role(role='edit', description='Can add new case, run case processing, clear processing results and case delete. Case is relevant to a particular user')
    return [role_read, role_edit]


def gen_default_applications():
    app_lungs = Application(name='lungs', description='Lungs segmentation on CT images using CNNs')
    app_lesions = Application(name='lesions', description='Lesions segmentation in lungs on CT images using CNNs')
    return [app_lungs, app_lesions]


def get_default_roles():
    role_read = Role.query.filter_by(role='read').first()
    role_edit = Role.query.filter_by(role='edit').first()
    # print(role_read.description)
    # print(role_edit.description)
    return [role_read, role_edit]


def get_default_applications():
    app_lungs = Application.query.filter_by(name='lungs').first()
    app_lesions = Application.query.filter_by(name='lesions').first()
    return [app_lungs, app_lesions]


# End of default Roles and Applications


@test_auth_app_login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@test_auth_app_login.request_loader
def load_user_from_request(request):
    is_internal = request.headers.get('X-internal')
    if is_internal is not None:
        if is_internal == 'True':
            u_uid = request.headers.get('X-uuid')
            # user_found = User.query.filter_by(user_uid=u_uid).first()
            return User.query.filter_by(user_uid=u_uid).first()
    return User.query.get(-1)
