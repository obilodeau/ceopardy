from flask import Flask, render_template, request, redirect, url_for
import flask_login


login_manager = flask_login.LoginManager()
users = {'host': {'pw': 'trebek'}}

def init_app(app):
    login_manager.init_app(app)
    login_manager.login_view = "/login"

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(username):
    if username not in users:
        return
    user = User()
    user.id = username
    return user

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    if username not in users:
        return

    user = User()
    user.id = username

    # DO NOT ever store passwords in plaintext and always compare password
    # hashes using constant-time comparison!
    user.is_authenticated = request.form['pw'] == users[username]['pw']
    return user

def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username']
    if request.form['password'] == users[username]['pw']:
        user = User()
        user.id = username
        flask_login.login_user(user)
        return redirect(url_for('host'))
    return 'Bad login'

def logout():
    flask_login.logout_user()
    return 'Logged out'


