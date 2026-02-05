import os
import cv2
import numpy as np
import time  # Essential for file-lock rectification
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer as Serializer
from PIL import Image, ImageEnhance

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'nirvana_heritage_secure_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Increase max content length to allow larger uploads (64MB)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024 

# Folder Configurations
UPLOAD_FOLDER = os.path.join('static', 'uploads')
PROCESSED_FOLDER = os.path.join('static', 'processed')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# --- MAIL CONFIGURATION ---
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'e23ai023@sdnbvc.edu.in'
app.config['MAIL_PASSWORD'] = 'jbny qhgn kljc ajmf'

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
login_manager = LoginManager(app)

login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- DATABASE MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HELPER FUNCTIONS ---
def send_reset_email(user):
    token = Serializer(app.config['SECRET_KEY']).dumps({'user_id': user.id})
    msg = Message('Nirvana Heritage - Password Reset Request',
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request, simply ignore this email.
'''
    mail.send(msg)

# --- PUBLIC ROUTES ---
@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/mission')
def mission():
    return render_template('mission.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        try:
            msg = Message(subject=f"New Royal Inquiry from {name}",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[app.config['MAIL_USERNAME']])
            msg.body = f"You have received a new inquiry.\n\nName: {name}\nEmail: {email}\n\nMessage:\n{message}"
            mail.send(msg)
            flash('Your message has been sent to the artisans. We will respond shortly.', 'success')
        except Exception as e:
            flash('Message could not be sent. Please try again later.', 'danger')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

# --- AUTH ROUTES ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_pw)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Account created! Welcome to Nirvana Heritage.', 'success')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('Username or Email already exists.', 'danger')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('splash'))

# --- ADMIN ROUTES ---
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Admin access required.', 'danger')
        return redirect(url_for('home'))
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Admin access required.', 'danger')
        return redirect(url_for('home'))
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@app.route('/make_admin/<int:user_id>', methods=['POST'])
@login_required
def make_admin(user_id):
    if not current_user.is_admin:
        flash('Admin access required.', 'danger')
        return redirect(url_for('home'))
    
    user = User.query.get(user_id)
    if user:
        user.is_admin = True
        db.session.commit()
        flash(f'{user.username} has been made an admin.', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/remove_admin/<int:user_id>', methods=['POST'])
@login_required
def remove_admin(user_id):
    if not current_user.is_admin:
        flash('Admin access required.', 'danger')
        return redirect(url_for('home'))
    
    if user_id == current_user.id:
        flash('You cannot revoke your own admin privileges.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    user = User.query.get(user_id)
    if user:
        user.is_admin = False
        db.session.commit()
        flash(f'{user.username} is no longer an admin.', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('Admin access required.', 'danger')
        return redirect(url_for('home'))
    
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f'{user.username} has been deleted.', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('admin_dashboard'))

# --- PASSWORD RESET FLOW ---
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            send_reset_email(user)
            flash('An email has been sent with instructions to reset your password.', 'info')
            return redirect(url_for('login'))
        else:
            flash('There is no account with that email.', 'warning')
    return render_template('reset_request.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    try:
        user_id = Serializer(app.config['SECRET_KEY']).loads(token, max_age=1800)['user_id']
    except:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    user = User.query.get(user_id)
    if request.method == 'POST':
        hashed_pw = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        user.password = hashed_pw
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html')

# --- IMAGE PROCESSING & EDITOR (CREATE) ---
@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)

            output_name = 'heritage_' + filename
            output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_name)
            
            # RECTIFICATION: Breath before read
            time.sleep(0.2)
            img = cv2.imread(input_path)
            if img is not None:
                denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
                pil_img = Image.fromarray(cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB))
                enhancer = ImageEnhance.Color(pil_img)
                pil_img = enhancer.enhance(1.2)
                pil_img.save(output_path)
                return render_template('create.html', processed=output_name)
            else:
                flash('Artifact unreadable. Please try a different format.', 'danger')
    
    return render_template('create.html', processed=None)

# --- ARTISAN AI PROCESSING ROUTE (Optimized) ---
@app.route('/process_artisan', methods=['POST'])
@login_required
def process_artisan():
    data = request.json
    filename = data.get('filename')
    operation = data.get('operation')
    
    input_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if not os.path.exists(input_path):
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
    if not os.path.exists(input_path):
        return jsonify({'error': f'Artifact not found: {filename}'}), 404

    # RECTIFICATION: OS Lock buffer and read validation
    time.sleep(0.2)
    img = cv2.imread(input_path)
    if img is None:
        return jsonify({'error': 'Artisan could not access the image stream.'}), 400
    
    h, w = img.shape[:2]
    if max(h, w) > 2500:
        scale = 2500 / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    if operation == 'dilation':
        kernel = np.ones((5,5), np.uint8)
        processed = cv2.dilate(img, kernel, iterations=1)
    elif operation == 'edges':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed = cv2.Canny(gray, 100, 200)
        processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
    elif operation == 'remove_bg':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        processed = cv2.bitwise_and(img, img, mask=mask)
    else:
        processed = img

    output_filename = f"artisan_{operation}_{filename}"
    output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
    cv2.imwrite(output_path, processed)
    
    return jsonify({'image_url': url_for('static', filename='processed/' + output_filename)})

# --- ADVANCED ROYAL CV FEATURES (Optimized for Timeout) ---
@app.route('/process_advanced', methods=['POST'])
@login_required
def process_advanced():
    data = request.json
    filename = data.get('filename')
    operation = data.get('operation')
    
    input_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if not os.path.exists(input_path):
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(input_path):
        return jsonify({'error': f'Artifact not found: {filename}'}), 404

    # RECTIFICATION: Wait for file release and validate read to prevent backend crash
    time.sleep(0.2)
    img = cv2.imread(input_path)
    if img is None: 
        return jsonify({'error': 'Royal Alchemy failed to read image source. Ensure file is not corrupt.'}), 400

    h, w = img.shape[:2]
    if max(h, w) > 2500:
        scale = 2500 / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    if operation == 'detect_objects':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        edged = cv2.Canny(blur, 30, 150)
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        processed = img.copy()
        cv2.drawContours(processed, contours, -1, (0, 215, 255), 2)

    elif operation == 'sketch':
        gray, _ = cv2.pencilSketch(img, s_sigma=60, r_sigma=0.07, shade_factor=0.05)
        processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    elif operation == 'detail':
        processed = cv2.detailEnhance(img, sigma_s=10, sigma_r=0.15)

    elif operation == 'sharpen':
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        processed = cv2.filter2D(img, -1, kernel)

    elif operation == 'bw':
        processed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)

    elif operation == 'vintage':
        kernel = np.array([[0.272, 0.534, 0.131],
                           [0.349, 0.686, 0.168],
                           [0.393, 0.769, 0.189]])
        processed = cv2.transform(img, kernel)
    
    elif operation == 'resize':
        width = int(img.shape[1] * 0.75)
        height = int(img.shape[0] * 0.75)
        processed = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)

    else:
        processed = img

    output_filename = f"royal_{operation}_{filename}"
    output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
    cv2.imwrite(output_path, processed)
    
    return jsonify({'image_url': url_for('static', filename='processed/' + output_filename)})

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)

# --- INITIALIZATION ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
        print("Nirvana Heritage Backend Active!")
    app.run(debug=True)