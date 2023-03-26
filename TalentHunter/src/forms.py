
from flask_wtf import Form
from wtforms import StringField, SubmitField, PasswordField, BooleanField, EmailField, DateField
from wtforms.validators import DataRequired, Length, Email, ValidationError, Optional


# def length_check(form,field):
#     if len(field.data) != 12:
#         raise ValidationError('Fields is in wrong format.')
    

# class AddRecordForm(Form):
#     record_num = StringField('Record No', validators=[DataRequired(), length_check])
#     ic = StringField('IC', validators=[DataRequired(), length_check])
#     book_code = StringField('Book Code', validators=[DataRequired(), length_check])
#     library_code = StringField('Library Code', validators=[DataRequired(), length_check])
#     borrowed_date = DateField('Borrowed Date', validators = [DataRequired("Date is required")])
#     availability = BooleanField('Book available?')
#     submit = SubmitField('Submit')
    

class LoginAndRegisterForm(Form):
    # login
    email_login = EmailField('Email', validators= [DataRequired(),Email()])
    password_login = PasswordField('Password', validators = [DataRequired(), Length(min=8, max=20)])

    # register
    name  = StringField('Username', validators=[DataRequired()])
    email_reg = EmailField('Email', validators= [DataRequired(),Email()])
    password_reg = PasswordField('Password', validators = [DataRequired(), Length(min=8, max=20)])
    password_conf = PasswordField('Password', validators = [DataRequired(), Length(min=8, max=20)])
