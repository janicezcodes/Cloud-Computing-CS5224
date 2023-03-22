import random
import string
from flask import request, session, redirect, url_for, render_template, flash
from sqlalchemy import null

from . models import Models
from . forms import LoginAndRegisterForm

from src import app


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


@app.route('/upload_cv')
def upload_cv():
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



if __name__ == '__main__':
    app.run()
