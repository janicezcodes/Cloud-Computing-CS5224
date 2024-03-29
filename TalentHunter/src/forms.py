
from flask_wtf import Form
from wtforms import StringField, SubmitField, PasswordField, BooleanField, EmailField, DateField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length, Email, ValidationError, Optional


class SearchForm(Form):
    title = SelectMultipleField(
        label='标签', choices=[('Account_Manager', 'Account Manager'), ('Business Analyst', 'Business Analyst'), ('Data Analyst', 'Data Analyst'),])
    submit = SubmitField(label='Submit')

class LoginForm(Form):
    email_login = EmailField('Email Address', validators= [DataRequired(),Email()])
    password_login = PasswordField('Password', validators = [DataRequired(), Length(min=8, max=20)])
    login = SubmitField('login-submit')

    
class RegisterForm(Form):
    name  = StringField('username', validators=[DataRequired()])
    email_reg = EmailField('email', validators= [DataRequired(),Email()])
    password_reg = PasswordField('password', validators = [DataRequired(), Length(min=8, max=20)])
    password_conf = PasswordField('Confirm Password', validators = [DataRequired(), Length(min=8, max=20)])
    register = SubmitField('register-submit')
