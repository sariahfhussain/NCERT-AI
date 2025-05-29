from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import random
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kimmikookiez@gmail.com'
app.config['MAIL_PASSWORD'] = 'gqdn bomk beku mexq'

db = SQLAlchemy(app)
mail = Mail(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    is_verified = db.Column(db.Boolean, default=False)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    user = User.query.filter_by(email=email).first()
    if user:
        flash('Email already registered.')
        return redirect(url_for('home'))
    otp = str(random.randint(100000, 999999))
    session['signup_data'] = {'name': name, 'email': email, 'password': password, 'otp': otp}
    # Send OTP
    msg = Message('Your OTP for NCERT AI', sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f'Your OTP is {otp}'
    mail.send(msg)
    return render_template('otp.html')

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    user_otp = request.form['otp']
    data = session.get('signup_data')
    if data and user_otp == data['otp']:
        user = User(name=data['name'], email=data['email'], password=data['password'], is_verified=True)
        db.session.add(user)
        db.session.commit()
        session.pop('signup_data', None)
        flash('Account created and verified! Please log in.')
        return redirect(url_for('home'))
    else:
        flash('Invalid OTP. Try again.')
        return render_template('otp.html')

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in first.')
        return redirect(url_for('home'))
    user = User.query.get(user_id)
    return render_template('class9-dashboard.html', user_name=user.name)

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user = User.query.filter_by(email=email, password=password, is_verified=True).first()
    if user:
        session['user_id'] = user.id
        flash('Logged in successfully!')
        return redirect(url_for('dashboard'))  # Redirect to dashboard
    else:
        flash('Invalid credentials or email not verified.')
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.')
    return redirect(url_for('home'))

@app.route('/science9')
def science9():
    return render_template('science9.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
