import random
import string
from flask import request, session, redirect, url_for, render_template, flash, Flask
import boto3

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
from werkzeug.utils import secure_filename

import io
import pdfminer
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
# from pdfminer.high_level import extract_text

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
                    return redirect(url_for('upload_files_to_s3'))  
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

# upload file to S3 bucket
def s3_upload_cv(file_to_upload, bucket, file_name, content_type):
    s3_client = boto3.client('s3')
    print('s3_client created')
    try:
        print('try upload s3')
        response = s3_client.put_object(Body=file_to_upload,
                                                Bucket=bucket,
                                                Key=file_name,
                                                ContentType=content_type)
        #upload_file(file_to_upload, bucket, file_name)
        print('after trying upload s3')
        print(f" ** Response - {response}")
    except Exception as e:
        print('Error in uploading to s3, ', e)


@app.route('/upload', methods=['GET', 'POST'])
def upload_files_to_s3():
    try:
        if session['user_available']:
            print('user_available')
            if request.method == 'GET':
                return render_template('upload.html')
            elif request.method == 'POST':
                print('file uploaded', request.files)
                # No file selected
                if 'fileselect[]' not in request.files:  # what the ‘file' defined in our html
                    flash(f' *** No files Selected', 'danger')
                file_to_upload = request.files['fileselect[]']
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

                    # s3_upload_cv(file_to_upload, bucket_name, file_name, content_type)
                    # add email and filename into postgreSQL
                    # models.addS3File({"email": session.get('current_user_email'), "file_name": file_name}) #uncomment to use sql 

                    # ---------------------------------------------------------------------------------
                    # calculate the matching scores and save to the RDS
                    # resume = request.files.get('CV.pdf')
                    # resume_txt = convert_pdf_2_text('/Users/apple/Documents/CS5224-TalentHunter/Apr5-clone/CS5224-TalentHunter/TalentHunter/src/CV.pdf')
                    resume_txt = convert_pdf_2_text(file_to_upload)

                    # get current user email
                    candidate_email = session.get('current_user_email')

                    #uncomment below to use sql 
                    candidate_id = models.getCandidateByEmail(candidate_email) 

                    jobs = models.getJobDescription()    # <class 'list'>

                    for job in jobs:
                        # type(job): <class 'sqlalchemy.engine.row.RowMapping'>
                        full_jd = job['description'] + job['responsibilities'] + job['qualifications']
                        text = [resume_txt,full_jd]
                        score = get_resume_score(text)
                        models.addMatch({"candidate_id": candidate_id['candidate_id'], "job_id": job['job_id'], "score": score})
                    # ---------------------------------------------------------------------------------
                    flash(f'Success - {file_to_upload} Is uploaded to {bucket_name}', 'success')

                else:
                    flash(f'Allowed file type is pdf.Please upload proper formats...', 'danger')   
        return render_template('upload.html')    
    except Exception as e:
        flash(str(e))
        return redirect(url_for('upload_files_to_s3'))


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
            # s3 = boto3.client('s3')
            s3 = boto3.client("th-s3", aws_access_key_id=os.getenv('AWS_ACCESS_KEY'), aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

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
def convert_pdf_2_text(path):

    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()

    device = TextConverter(rsrcmgr, retstr)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    with open(path, 'rb') as fp:
        for page in PDFPage.get_pages(fp, set()):
            interpreter.process_page(page)
        text = retstr.getvalue()

    device.close()
    retstr.close()

    return text



    
# Generate matching scores in percentage
def get_resume_score(text):
    cv = CountVectorizer(stop_words='english')
    count_matrix = cv.fit_transform(text)
     
    #get the match percentage
    matchPercentage = cosine_similarity(count_matrix)[0][1] * 100
    matchPercentage = round(matchPercentage, 2) # round to two decimal
     
    return matchPercentage



if __name__ == '__main__':
    app.run()