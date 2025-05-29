from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
import requests
from utils.pdf_processor import PDFProcessor
from utils.rag_utils import RAGSystem
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'kimmikookiez@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'gqdn bomk beku mexq')

db = SQLAlchemy(app)
mail = Mail(app)

# RAG and LLM setup
pdf_processor = PDFProcessor()
rag_system = RAGSystem()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200))  # Hashed
    is_verified = db.Column(db.Boolean, default=False)

@app.before_first_request
def initialize_rag():
    """Initialize RAG system if not already done"""
    if not os.path.exists("utils/vector_store.faiss"):
        if not os.path.exists("static/ncert_pdfs"):
            os.makedirs("static/ncert_pdfs")
        documents = pdf_processor.process_directory("static/ncert_pdfs")
        rag_system.create_vector_store(documents)

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
    session['signup_data'] = {
        'name': name,
        'email': email,
        'password': generate_password_hash(password),
        'otp': otp
    }
    # Send OTP
    msg = Message('Your OTP for NCERT AI', sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f'Your OTP is {otp}'
    try:
        mail.send(msg)
    except Exception as e:
        flash('Failed to send OTP email. Please try again.')
        return redirect(url_for('home'))
    return render_template('otp.html')

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    user_otp = request.form['otp']
    data = session.get('signup_data')
    if data and user_otp == data['otp']:
        user = User(
            name=data['name'],
            email=data['email'],
            password=data['password'],
            is_verified=True
        )
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
    user = User.query.filter_by(email=email, is_verified=True).first()
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        flash('Logged in successfully!')
        return redirect(url_for('dashboard'))
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

# --- LLM Integration using Ollama (local, free) ---
def ollama_generate(prompt, model="phi3"):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        result = response.json()
        return result.get("response", "Sorry, I couldn't generate an answer.")
    except Exception as e:
        return "Sorry, there was an error connecting to the LLM."

@app.route('/ask', methods=['POST'])
def ask_question():
    if 'user_id' not in session:
        return jsonify({"error": "Please login first"}), 401

    data = request.json
    question = data.get('question')
    chapter = data.get('chapter')

    if not question:
        return jsonify({"error": "Question is required"}), 400

    # Search with filters
    filters = {}
    if chapter:
        filters["chapter"] = f"Chapter {chapter.split('_')[1].replace('C', '')}"

    results = rag_system.search(question, filters=filters)

    if not results:
        return jsonify({
            "answer": "I couldn't find relevant information in the textbook.",
            "sources": []
        })

    # Compose context for LLM
    context = "\n".join([f"Source {i+1}: {res['text']}" for i, res in enumerate(results)])
    prompt = f"""Answer this question based on the NCERT textbook context:

Question: {question}

Context:
{context}

Answer in simple language suitable for a 9th grade student:"""

    answer = ollama_generate(prompt)

    return jsonify({
        "answer": answer,
        "sources": list(set(res['metadata']['source'] for res in results))
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
