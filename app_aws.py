
import os
import cv2
import time
import uuid
import boto3
import numpy as np
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, send_from_directory
)
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance
from botocore.exceptions import ClientError

# ======================================================
# 1. FLASK APP CONFIG
# ======================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'nirvana_heritage_aws_2026'

UPLOAD_FOLDER = 'static/uploads'
PROCESSED_FOLDER = 'static/processed'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

# ======================================================
# 2. AWS CONFIG (IAM BASED)
# ======================================================
AWS_REGION = "us-east-1"

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
sns = boto3.client("sns", region_name=AWS_REGION)

USERS_TABLE = dynamodb.Table("NirvanaUsers")
LOGS_TABLE = dynamodb.Table("NirvanaLogs")

SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:NirvanaAlerts"

# ======================================================
# 3. AUTH SETUP
# ======================================================
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ======================================================
# 4. USER MODEL (DYNAMODB)
# ======================================================
class User(UserMixin):
    def __init__(self, user_id, username, email, password, is_admin=False):
        self.id = user_id
        self.username = username
        self.email = email
        self.password = password
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    res = USERS_TABLE.get_item(Key={"user_id": user_id})
    if "Item" in res:
        u = res["Item"]
        return User(
            u["user_id"],
            u["username"],
            u["email"],
            u["password"],
            u.get("is_admin", False)
        )
    return None

# ======================================================
# 5. SNS HELPER
# ======================================================
def notify_admin(subject, message):
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except ClientError as e:
        print("SNS Error:", e)

# ======================================================
# 6. PUBLIC ROUTES
# ======================================================
@app.route("/")
def splash():
    return render_template("splash.html")

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/mission")
def mission():
    return render_template("mission.html")

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ✅ REQUIRED TO FIX BuildError
@app.route("/reset_request")
def reset_request():
    return "", 204   # blank page, no access

# ======================================================
# 7. AUTH ROUTES (LOGIN INTENTIONALLY BLOCKED)
# ======================================================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    flash("Signup disabled for AWS deployment", "danger")
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        flash("Invalid credentials", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("splash"))

# ======================================================
# 8. IMAGE CREATE (WORKS AFTER LOGIN — FOR DEMO)
# ======================================================
@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("No file selected", "danger")
            return redirect(url_for("create"))

        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)

        img = cv2.imread(input_path)

        denoised = cv2.fastNlMeansDenoisingColored(
            img, None, 10, 10, 7, 21
        )

        pil_img = Image.fromarray(
            cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB)
        )

        pil_img = ImageEnhance.Color(pil_img).enhance(1.2)

        output_name = "heritage_" + filename
        output_path = os.path.join(PROCESSED_FOLDER, output_name)
        pil_img.save(output_path)

        LOGS_TABLE.put_item(Item={
            "log_id": str(uuid.uuid4()),
            "action": "image_processed",
            "file": output_name
        })

        notify_admin("Image Processed", "Image updated via AWS app")

        return render_template("create.html", processed=output_name)

    return render_template("create.html")

# ======================================================
# 9. ADVANCED PROCESSING
# ======================================================
@app.route("/process_advanced", methods=["POST"])
@login_required
def process_advanced():
    data = request.json
    filename = data["filename"]
    operation = data["operation"]

    input_path = os.path.join(PROCESSED_FOLDER, filename)
    img = cv2.imread(input_path)

    if operation == "edges":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed = cv2.Canny(gray, 100, 200)
        processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
    elif operation == "bw":
        processed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
    elif operation == "sharpen":
        kernel = np.array([
            [-1,-1,-1],
            [-1, 9,-1],
            [-1,-1,-1]
        ])
        processed = cv2.filter2D(img, -1, kernel)
    else:
        processed = img

    output_name = f"royal_{operation}_{filename}"
    output_path = os.path.join(PROCESSED_FOLDER, output_name)
    cv2.imwrite(output_path, processed)

    return jsonify({
        "image_url": url_for("static", filename="processed/" + output_name)
    })

# ======================================================
# 10. DOWNLOAD
# ======================================================
@app.route("/download/<filename>")
@login_required
def download(filename):
    return send_from_directory(
        PROCESSED_FOLDER, filename, as_attachment=True
    )

# ======================================================
# 11. RUN ON EC2
# ======================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
