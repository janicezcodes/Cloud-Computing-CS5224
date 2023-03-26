import random
import string
from flask import request, session, redirect, url_for, render_template, flash, Flask
from sqlalchemy import null
import boto3

from . models import Models
from . forms import *

from src import app

import os
# from flask_bootstrap import Bootstrap
# from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename


models = Models()

# @app.route('/')
# def index():
#     return render_template('login.html')


@app.route('/login_and_reg', methods=['GET', 'POST'])
def login_and_reg():
    try:
        login_and_reg_form = LoginAndRegisterForm(request.form)
        if request.method == 'POST':    
            em_login = login_and_reg_form.email_login.data
            password_login = login_and_reg_form.password_login.data 
            newname = login_and_reg_form.name.data
            email_reg = login_and_reg_form.email_reg.data
            password_reg = login_and_reg_form.password_reg.data
            password_conf = login_and_reg_form.password_conf.data

            if em_login != None:
                log = models.getCandidateByEmail(em_login)
                if log.password == password_login:     # login
                    session['current_user'] = em_login
                    session['user_available'] = True
                    return redirect(url_for('upload_cv'))     
                else:
                    flash('Cannot sign in. Email or password is wrong.')
            if newname != None:
                if password_reg == password_conf:
                    models.addCandidate({"candidate_id": generate_random_id(9),
                                         "name": newname,
                                         "email":email_reg, 
                                         "password": password_reg})
                else:
                    flash('Passwords are not same.')
            return redirect(url_for('login_and_reg'))    
        return render_template('login_and_reg.html', login_and_reg_form=login_and_reg_form)
    except Exception as e:
        flash(str(e))
        return redirect(url_for('login_and_reg'))


# @app.route('/upload_cv')
# def upload_cv():
    # try:
    #     if session['user_available']:
    #         booksAndRecords = models.getRecords()
    #         return render_template('records.html', booksAndRecords=booksAndRecords)
    #     flash('User is not Authenticated')
    #     return redirect(url_for('index'))
    # except Exception as e:
    #     flash(str(e))


# generate random id
def generate_random_id(length):
    # 字母和数字的组合
    characters = string.ascii_letters + string.digits
    # 生成随机字符串
    return ''.join(random.choice(characters) for i in range(length))



# ---------------------------------------------------------------------------------
# Set allowed extensions to allow only upload excel files
ALLOWED_EXTENSIONS = set(['pdf'])
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# upload file to S3 bucket
def s3_upload_cv(file_name, bucket):
    object_name = file_name
    s3_client = boto3.client('s3')
    response = s3_client.upload_file(file_name, bucket, object_name)
    return response


@app.route('/upload_files_to_s3', methods=['GET', 'POST'])
def upload_files_to_s3():
    try:
        if session['user_available']:
            if request.method == 'POST':

                # No file selected
                if 'file' not in request.files:  # what the ‘file' defined in our html
                    flash(f' *** No files Selected', 'danger')

                file_to_upload = request.files['file']
                # content_type = request.mimetype

                # if empty files
                if file_to_upload.filename == '':
                    flash(f' *** No files Selected', 'danger')

                # file uploaded and check
                if file_to_upload and allowed_file(file_to_upload.filename):

                    file_name = secure_filename(file_to_upload.filename)

                    print(f" *** The file name to upload is {file_name}")
                    print(f" *** The file full path  is {file_to_upload}")

                    bucket_name = "talenthunterbucket"

                    s3_upload_cv(file_name, bucket_name, file_name)
                    # url = create_presigned_url(bucket_name, file_name)

                    # add session[current_user] and filename into postgreSQL, not create url

                    flash(f'Success - {file_to_upload} Is uploaded to {bucket_name}', 'success')

                else:
                    flash(f'Allowed file type is pdf.Please upload proper formats...', 'danger')

        # return redirect(url_for('index'))
    except Exception as e:
        flash(str(e))


# ------------------------------------------------------------------------------------------
@app.route('/search_candidate', methods=['GET', 'POST'])
def search_candidate():
    '''
    1. get selected job
    2. sql query
    3. return result
    4. get candidate selected
    5. display S3 file
    '''
    s3 = boto3.client('s3')
    s3.download_file('BUCKET_NAME', 'OBJECT_NAME', 'FILE_NAME')


if __name__ == '__main__':
    app.run()
