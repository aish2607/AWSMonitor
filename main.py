from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session,flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from CostReport import *
app = Flask(__name__)

app.secret_key = 'your secret key'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'pythonlogin'

mysql = MySQL(app)

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'loggedin' in session:
            return f(*args, **kwargs)
        else:
            flash("You need to login first")
            return redirect(url_for('login'))

    return wrap
@app.route('/pythonlogin/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            if(session['username']=='varshini'):
                return redirect(url_for('admin_home'))
            return redirect(url_for('home'))
        else:
            msg = 'Incorrect username/password!'
    return render_template('index.html', msg=msg)

@app.route('/pythonlogin/logout')
@login_required
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/pythonlogin/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        access = request.form['access']
        secret = request.form['secret']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s, %s, %s)', (username, password, email, access, secret))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html',msg=msg)


@app.route('/pythonlogin/home')
@login_required
def home():
    if 'loggedin' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/pythonlogin/admin_home',methods=['GET', 'POST'])
@login_required
def admin_home():
    if 'loggedin' in session:
        return render_template('admin_home.html', username=session['username'])
    return redirect(url_for('login'))


@app.route('/pythonlogin/profile')
@login_required
def profile():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        if(session['username']=='varshini'):
            return render_template('admin_profile.html', account=account)
        return render_template('profile.html', account=account)
    return redirect(url_for('login'))

@app.route('/pythonlogin/admin_profile')
@login_required
def admin_profile():
    if 'loggedin' in session:
        conn=MySQLdb.connect(host='localhost',database='pythonlogin',user='root',password='password')
        cursor=conn.cursor()
        cursor.execute("select username,email,password,access,secret from accounts WHERE username!='varshini'")
        rows=cursor.fetchall()
        return render_template('admin_profile.html', account=rows)
    return redirect(url_for('login'))

@app.route('/pythonlogin/cost')
@login_required
def costusage():
    main()
    f = open("report.csv","r")
    #print(f)

    row=f.readlines()#[0].split(",")
    #print(row)
    d1=row[0].split(",")
    #print(d)
    d=dict()
    results=[]

    #print(type(d['#Time Period']))
    for i in range(1,len(row)):
        d=dict()
        r=row[i].split(",")
        d['#Time Period']=r[0]
        d['Linked Account']=r[1]
        d['Service']=r[2]
        d['Amount']=r[3]
        d['Unit']=r[4]
        d['Estimated']=r[5]
        results.append(d)
    return render_template('costusage.html',results=results)



app.run(debug=True)