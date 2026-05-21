from datetime import datetime, timedelta
import csv
import io
import os

from dotenv import load_dotenv

from flask import Flask, request, jsonify, session, Response, send_from_directory
from flask_cors import CORS
from werkzeug.utils import safe_join

from config import Config
from extensions import db, bcrypt, limiter
from models import User, AuditLog
from security import (
    login_required,
    admin_required,
    write_audit_log,
    add_security_headers
)
from camera import CameraService

load_dotenv()

app = Flask(
    __name__,
    static_folder="../frontend",
    static_url_path=""
)

app.config.from_object(Config)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///instance/secure_cctv.db"
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

CORS(app, supports_credentials=True)

db.init_app(app)
bcrypt.init_app(app)
limiter.init_app(app)

camera_source = os.getenv(
    "CAMERA_SOURCE",
    ""
)

camera_service = (
    CameraService(camera_source)
    if camera_source
    else None
)

app.after_request(add_security_headers)

# FRONTEND

@app.route("/")
def serve_login():
    return send_from_directory(
        "../frontend",
        "index.html"
    )


@app.route("/<path:filename>")
def serve_frontend(filename):

    safe_path = safe_join(
        "../frontend",
        filename
    )

    if safe_path is None:
        return jsonify({
            "error":
            "Invalid path"
        }), 400

    return send_from_directory(
        "../frontend",
        filename
    )

# SETUP ADMIN

@app.route("/api/setup", methods=["POST"])
def setup_admin():

    existing_admin = User.query.filter_by(
        username="admin"
    ).first()

    if existing_admin:
        return jsonify({
            "message":
            "Admin already exists"
        }), 200

    admin = User(
        username="admin",
        email="admin@example.com",
        role="admin"
    )

    admin.set_password(
        "admin123"
    )

    db.session.add(admin)
    db.session.commit()

    return jsonify({
        "message":
        "Admin created"
    })

# LOGIN

@app.route(
    "/api/auth/login",
    methods=["POST"]
)
@limiter.limit(
    "5 per minute"
)
def login():

    data = request.get_json() or {}

    username = data.get(
        "username",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    )

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:

        write_audit_log(
            username,
            "Failed login"
        )

        return jsonify({
            "error":
            "Invalid credentials"
        }), 401

    if user.locked_until and datetime.utcnow() < user.locked_until:

        return jsonify({
            "error":
            "Account locked"
        }), 423

    if not user.is_active:

        return jsonify({
            "error":
            "Account disabled"
        }), 403

    if not user.check_password(
        password
    ):

        user.failed_attempts += 1

        if user.failed_attempts >= 5:

            user.locked_until = (
                datetime.utcnow()
                + timedelta(
                    minutes=15
                )
            )

        db.session.commit()

        return jsonify({
            "error":
            "Invalid credentials"
        }), 401

    user.failed_attempts = 0
    user.locked_until = None

    db.session.commit()

    session.permanent = True

    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role

    write_audit_log(
        user.username,
        "Logged in"
    )

    return jsonify({
        "message":
        "Login successful",

        "user": {
            "username":
            user.username,

            "role":
            user.role
        }
    })

# LOGOUT

@app.route(
    "/api/auth/logout",
    methods=["POST"]
)
@login_required
def logout():

    write_audit_log(
        session.get(
            "username"
        ),
        "Logged out"
    )

    session.clear()

    return jsonify({
        "message":
        "Logged out"
    })

# CURRENT USER

@app.route(
    "/api/auth/me"
)
@login_required
def current_user():

    return jsonify({
        "username":
        session.get(
            "username"
        ),

        "role":
        session.get(
            "role"
        )
    })

# DASHBOARD

@app.route(
    "/api/dashboard/stats"
)
@login_required
def dashboard_stats():

    total_users = User.query.count()

    total_logs = AuditLog.query.count()

    return jsonify({

        "camera_status":
        "ONLINE",

        "online_cameras":
        1,

        "active_users":
        total_users,

        "total_logs":
        total_logs,

        "devices":
        total_users

    })

# CAMERA

@app.route(
    "/api/camera/stream"
)
@login_required
def camera_stream():

    if camera_service is None:

        return jsonify({
            "error":
            "Camera unavailable"
        }), 503

    return Response(
        camera_service.generate_frames(),
        mimetype=
        "multipart/x-mixed-replace; boundary=frame"
    )


@app.route(
    "/api/camera/status"
)
@login_required
def camera_status():

    if camera_service is None:

        return jsonify({
            "camera":
            "Main Camera",

            "status":
            "UNAVAILABLE"
        })

    is_online = camera_service.connect()

    return jsonify({

        "camera":
        "Main Camera",

        "status":
        "ONLINE"
        if is_online
        else
        "OFFLINE"

    })

# USERS

@app.route(
    "/api/users"
)
@admin_required
def get_users():

    users = User.query.all()

    return jsonify([

        {
            "id":
            u.id,

            "username":
            u.username,

            "email":
            u.email,

            "role":
            u.role,

            "is_active":
            u.is_active
        }

        for u in users

    ])

# LOGS

@app.route(
    "/api/logs"
)
@admin_required
def get_logs():

    logs = AuditLog.query.order_by(
        AuditLog.created_at.desc()
    ).limit(200).all()

    return jsonify([

        {
            "username":
            log.username,

            "action":
            log.action,

            "ip_address":
            log.ip_address,

            "created_at":
            log.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

        for log in logs

    ])

@app.cli.command(
    "init-db"
)
def init_db():

    db.create_all()

    print(
        "DB initialized"
    )

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                8000
            )
        ),
        debug=False
    )
