from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, PasswordField
from wtforms.validators import DataRequired, EqualTo, Email



class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('login')

class ProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    age_limit = SelectField('Age Limit', choices=[('All', 'All'), ('Kids', 'Kids')], validators=[DataRequired()])
    submit = SubmitField('Create Profile')


class RegisterForm(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired(), Email()])
    password = PasswordField('password', validators=[DataRequired()])
    password2 = PasswordField('confirm password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrado')

class LogAdminForm(FlaskForm):
    email = StringField('email', validators=[DataRequired(), Email()])
    password = PasswordField('password', validators=[DataRequired()])
    submit = SubmitField('login')

class SearchForm(FlaskForm):
    search_query = StringField('Buscar', validators=[DataRequired()])
    submit = SubmitField('Buscar')