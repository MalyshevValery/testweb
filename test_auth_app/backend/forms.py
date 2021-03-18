from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from test_auth_app.backend.db_models import User


class LoginForm(FlaskForm):
    # username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit_field = SubmitField('Log In')


class RegistrationForm(FlaskForm):
    # username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=32, message='Password length should be from 8 to 32 symbols')])
    password_confirm = PasswordField('Repeat password', validators=[DataRequired(), EqualTo('password')])
    submit_field = SubmitField('Submit request')

    def validate_username(self, username):
        user_q = User.query.filter_by(username=username.data).first()
        if user_q is not None:
            raise ValidationError('{} already registered'.format(username.data))

    def validate_email(self, email):
        email_q = User.query.filter_by(email=email.data).first()
        if email_q is not None:
            raise ValidationError('{} already registered'.format(email.data))
