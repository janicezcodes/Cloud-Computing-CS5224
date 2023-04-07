import random
import string
from flask import request, session, redirect, url_for, render_template, flash, Flask
import boto3
import base64

import nltk
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

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

import re
import operator
from nltk.tokenize import word_tokenize 
from nltk.corpus import stopwords
set(stopwords.words('english'))

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


models = Models()
bucket_name = "talenthunterbucket"


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('login_and_reg.html')
    
    elif request.method == 'POST':  
        try:
            #login
            print(request.form)
            if len(request.form)==3:
                em_login = request.form['log-email']
                print('em_login', em_login)
                password_login = request.form['password']
                
                log = models.getCandidateByEmail(em_login)
                if em_login == 'admin@gmail.com' and password_login == log.password:
                    return redirect(url_for('search_candidate')) 
                elif password_login == log.password:     
                    session['current_user_email'] = em_login
                    session['user_available'] = True
                    return redirect(url_for('upload_file'))  
                else:
                    flash('Cannot sign in. Email or password is wrong.')
                    return redirect(url_for('index'))

            # register
            elif len(request.form)==5:
                newname = request.form['reg-username']
                email_reg = request.form['reg-email']
                password_reg = request.form['new-password']
                password_conf = request.form['confirm-password']
                
                if password_reg and password_reg == password_conf:
                    models.addCandidate({"candidate_id": generate_random_id(9),
                                        "name": newname,
                                        "email":email_reg, 
                                        "password": password_reg})
                    flash('Register successfully. Please login.')
                    return redirect(url_for('index'))
                else:
                    flash('Fill in the correct password.')
                    return render_template('login_and_reg.html', RegisterForm=request.form)

            return render_template('login_and_reg.html')
        except Exception as e:
            flash(str(e))
            return render_template('login_and_reg.html') 
        
        
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

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    try:
        if session['user_available']:
            print('user_available')
            if request.method == 'GET':
                return render_template('upload.html')
            elif request.method == 'POST':
                print('file uploaded', request.files)
                # No file selected
                if 'fileselect[]' not in request.files:  
                    flash(f' *** No files Selected', 'danger')
                file_to_upload = request.files['fileselect[]']
                content_type = request.mimetype
                print('file_to_upload', file_to_upload)
                print('file_name', file_to_upload.filename)
                # if empty files
                if not file_to_upload.filename:
                    flash(f' *** No files Selected', 'danger')

                # file uploaded and check
                if file_to_upload and allowed_file(file_to_upload.filename):
                    file_name = secure_filename(file_to_upload.filename)
                    print(f" *** The file name to upload is {file_name}")
                    print(f" *** The file full path  is {file_to_upload}")
                    
                    encoded_data = base64.b64encode(file_to_upload.read()).decode('utf-8')

                    # add email and filename into postgreSQL
                    # var_data = convert_from(decode('MTExMQ==', 'base64'), 'UTF8')  
                    models.addEncodedPDF({"email": session.get('current_user_email'), "encoded_data": encoded_data}) #uncomment to use sql 

                    # ---------------------------------------------------------------------------------
                    # calculate the matching scores and save to the RDS
                    resume = file_to_upload
                    # get current user email
                    candidate_email = session.get('current_user_email')
                    #uncomment below to use sql 
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
        return render_template('upload.html')    
    except Exception as e:
        flash(str(e))
        return redirect(url_for('upload_file'))


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
    return render_template('search.html')


# ------------------------------------------------------------------------------------------

@app.route('/show_results', methods=['GET', 'POST'])
def show_results():
    '''
    1. sql query
    2. return result
    3. select candidate
    '''
    try:
        if session['user_available']:
            if request.method == 'GET':
                title = session['search_title']
                candidates_log = models.getMatchScoresByTitle(title)
                # candidates_info = {}
                # for log in candidates_log:
                #     key = log.name # change this if wanna select by others
                #     candidates_info[key] = log.email
                # session['keyDict'] = candidates_info
                return render_template('show_results.html', scores=candidates_log)
            elif request.method == 'POST':
                # HR select candidate, need to add button in html
                selected_key = request.form['name']
                # candidates_info = session.get('keyDict')
                # email_selected = candidates_info['selected_key']
                session['candidate_selected'] = selected_key
                return redirect(url_for('display_cv_pdf'))
        flash('You are not an Authenticated User')
        return redirect(url_for('index'))
    except Exception as e:
        flash(str(e))
        return redirect(url_for('index'))


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

@app.route('/display_cv_pdf', methods=["GET"])
def display_cv_pdf():
    if session['user_available']:
        candidate_selected = session.get('candidate_selected')
        encoded_data = models.getEncodedPDF(candidate_selected)
        return render_template("test.html", encoded_data=encoded_data)
        # pdf_data = base64.b64decode(pdf_b64)
        # return Response(pdf_data, mimetype='application/pdf')

if __name__ == '__main__':
    app.run()