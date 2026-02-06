import os
import cv2
import uuid
import boto3
import time
from datetime import datetime
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, send_from_directory
)
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'nirvana_heritage_secure_2026'

# ---------------- AWS CONFIG ----------------
AWS_REGION = 'us-east-1'
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:253490749648:aws_capstone_pp'
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns = boto3.client('sns', region_name=AWS_REGION)

users_table = dynamodb.Table('NH_Users')
logs_table = dynamodb.Table('NH_AdminLogs')

# ---------------- FILE CONFIG ----------------
UPLOAD_FOLDER = 'static/uploads'
PROCESSED_FOLDER = 'static/processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# ---------------- AUTH CONFIG ----------------
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------------- USER MODEL ----------------
class User(UserMixin):
    def __init__(self, email, username, password, is_admin=False):
        self.id = email
        self.email = email
        self.username = username
        self.password = password
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(email):
    try:
        response = users_table.get_item(Key={'email': email})
        user = response.get('Item')
        if user:
            return User(
                user['email'],
                user['username'],
                user['password'],
                user.get('is_admin', False)
            )
    except Exception as e:
        print("User load error:", e)
    return None

# ---------------- AWS HELPERS ----------------
def send_sns(subject, message):
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except ClientError as e:
        print("SNS Error:", e)

def log_admin_action(message):
    logs_table.put_item(Item={
        'log_id': str(uuid.uuid4()),
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    })

# ---------------- PUBLIC ROUTES ----------------
@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/mission')
def mission():
    return render_template('mission.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        send_sns(
            "New Contact Inquiry",
            f"Name: {request.form.get('name')}\n"
            f"Email: {request.form.get('email')}\n"
            f"Message: {request.form.get('message')}"
        )
        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

# ---------------- AUTH ROUTES ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']

        if users_table.get_item(Key={'email': email}).get('Item'):
            flash('User already exists', 'danger')
            return redirect(url_for('signup'))

        users_table.put_item(Item={
            'email': email,
            'username': request.form['username'],
            'password': bcrypt.generate_password_hash(
                request.form['password']
            ).decode(),
            'is_admin': False
        })

        send_sns("New Signup", f"{email} registered")
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        response = users_table.get_item(
            Key={'email': request.form['email']}
        )
        user = response.get('Item')

        if user and bcrypt.check_password_hash(
            user['password'],
            request.form['password']
        ):
            login_user(User(
                user['email'],
                user['username'],
                user['password'],
                user.get('is_admin', False)
            ))
            send_sns("User Login", f"{user['username']} logged in")
            return redirect(url_for('home'))

        flash('Invalid credentials', 'danger')

    return render_template('login.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        flash(
            'If this email exists, a reset link will be sent.',
            'info'
        )
        return redirect(url_for('login'))
    return render_template('reset_request.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('splash'))

# ---------------- HOME ROUTE ----------------
@app.route('/home')
@login_required
def home():
    return render_template('home.html')

# ---------------- ADMIN ROUTES ----------------
@app.route('/admin')
@login_required
def admin():
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Admins only!', 'danger')
        return redirect(url_for('home'))

    return render_template(
        'admin_dashboard.html',
        users=users_table.scan().get('Items', []),
        logs=logs_table.scan().get('Items', [])
    )

@app.route('/make_admin/<email>', methods=['POST'])
@login_required
def make_admin(email):
    if not current_user.is_admin:
        return redirect(url_for('home'))

    users_table.update_item(
        Key={'email': email},
        UpdateExpression="SET is_admin = :a",
        ExpressionAttributeValues={':a': True}
    )

    log_admin_action(f"{email} promoted to admin")
    return redirect(url_for('admin_dashboard'))

# ---------------- IMAGE PROCESSING ----------------
@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)

        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)

        time.sleep(0.2)
        img = cv2.imread(input_path)
        img = cv2.fastNlMeansDenoisingColored(
            img, None, 10, 10, 7, 21
        )

        output_name = f"heritage_{filename}"
        cv2.imwrite(
            os.path.join(PROCESSED_FOLDER, output_name),
            img
        )

        return render_template(
            'create.html',
            processed=output_name
        )

    return render_template('create.html')

@app.route('/download/<filename>')
@login_required
def download(filename):
    return send_from_directory(
        PROCESSED_FOLDER,
        filename,
        as_attachment=True
    )

# ---------------- START ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

