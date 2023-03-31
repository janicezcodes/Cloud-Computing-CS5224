# import sys
# # if there are no conflicting packages in the default Python Libs =>
# sys.path.append("/usr/home/username/pdfminer")



import random
import string
from flask import request, session, redirect, url_for, render_template, flash, Flask
from sqlalchemy import null
import boto3

import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
from . models import Models
from . forms import *

from src import app

import os
# from flask_bootstrap import Bootstrap
# from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

import io
import pdfminer
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
#Docx resume
# import docx2txt
#Wordcloud
import re
import operator
from nltk.tokenize import word_tokenize 
from nltk.corpus import stopwords
set(stopwords.words('english'))
# from wordcloud import WordCloud
from nltk.probability import FreqDist
# import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


models = Models()
bucket_name = "talenthunterbucket"

@app.route('/')
def index():
    return render_template('login_and_reg.html')


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
                    session['current_user_email'] = em_login
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



# generate random id
def generate_random_id(length):
    # 字母和数字的组合
    characters = string.ascii_letters + string.digits
    # 生成随机字符串
    return ''.join(random.choice(characters) for i in range(length))


# ---------------------------------------------------------------------------------
# Set allowed extensions to allow only upload pdf files
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
                # if empty files
                if file_to_upload.filename == '':
                    flash(f' *** No files Selected', 'danger')

                # file uploaded and check
                if file_to_upload and allowed_file(file_to_upload.filename):
                    file_name = secure_filename(file_to_upload.filename)
                    print(f" *** The file name to upload is {file_name}")
                    print(f" *** The file full path  is {file_to_upload}")

                    s3_upload_cv(file_name, bucket_name, file_name)
                    # add email and filename into postgreSQL
                    models.addS3File({"email": session.get('current_user_email'), "file_name": file_name})

                    # ---------------------------------------------------------------------------------
                    # calculate the matching scores and save to the RDS
                    resume = file_to_upload
                    # get current user email
                    candidate_email = session.get('current_user_email')
                    candidate_id = models.getCandidateByEmail(candidate_email)

                    jobs = models.getJobDescription()

                    for job in jobs:
                        full_jd = job.description.data + job.responsibilities.data + job.qualifications.data
                        text = [resume, full_jd] 
                        score = get_resume_score(text)
                        models.addMatch({"candidate_id": candidate_id, "job_id": job.job_id.data, "score": score})
                    # ---------------------------------------------------------------------------------
                    flash(f'Success - {file_to_upload} Is uploaded to {bucket_name}', 'success')

                else:
                    flash(f'Allowed file type is pdf.Please upload proper formats...', 'danger')

        # return redirect(url_for('index'))
    except Exception as e:
        flash(str(e))


# ------------------------------------------------------------------------------------------
@app.route('/search', methods=['GET', 'POST'])
def search_candidate():
    ''' get selected job'''
   
    #  这里用户需要选择title，然后去数据库查找，所以methods=['GET', 'POST']
    if request.method == 'POST': 
        title = request.values.get('title')
        session['user_available'] = True    # to generate results in the next page
        session['search_title'] = title
        return redirect(url_for('show_results'))


# ------------------------------------------------------------------------------------------

@app.route('/show_results')
def show_results():
    '''
    1. sql query
    2. return result
    3. get candidate selected
    4. display S3 file
    '''
    try:
        if session['user_available']:
            title = session['search_title']
            candidates_log = models.getMatchScoresByTitle(title)
            candidates_show = []
            s3 = boto3.client('s3')
            for log in candidates_log:
                candidate_email = log.email
                file_name = models.getS3FileName(candidate_email)
                url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': file_name+'.pdf'}, ExpiresIn=3600)
                log['s3_url'] = url
                candidates_show.append(log)
            return render_template('show_results.html', scores=candidates_show)
        flash('You are not an Authenticated User')
        return redirect(url_for('login_and_reg'))
    except Exception as e:
        flash(str(e))
        return redirect(url_for('login_and_reg'))


# Read pdf file
def read_pdf_resume(pdf_doc):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle)
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(pdf_doc, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True,check_extractable=True):           
            page_interpreter.process_page(page)     
        text = fake_file_handle.getvalue() 
    # close open handles      
    converter.close() 
    fake_file_handle.close() 
    if text:     
        return text
    
# Generate matching scores in percentage
def get_resume_score(text):
    cv = CountVectorizer(stop_words='english')
    count_matrix = cv.fit_transform(text)
    #Print the similarity scores
    print("\nSimilarity Scores:")
     
    #get the match percentage
    matchPercentage = cosine_similarity(count_matrix)[0][1] * 100
    matchPercentage = round(matchPercentage, 2) # round to two decimal
     
    return matchPercentage



if __name__ == '__main__':
    app.run()


