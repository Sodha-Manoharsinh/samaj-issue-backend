import cloudinary.uploader
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from utils.email_utils import send_email
from utils.otp_utils import generate_otp
from datetime import datetime, timedelta
from config import Config
import cloudinary
from supabase import create_client

auth_bp = Blueprint("auth", __name__)

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# -------------------------------
# STEP 1: Request Signup (send OTP)
# -------------------------------

@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")

    # ✅ 1. Check if email already exists in Supabase
    response = supabase.table("user").select("email").eq("email", email).execute()
    if response.data and len(response.data) > 0:
        return jsonify({"error": "Email already registered"}), 400

    # ✅ 2. Generate OTP and expiry
    code = generate_otp()
    expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat()

    # ✅ 3. Send OTP via email
    if not send_email(to=email, otp_code=code):
        return jsonify({"error": "Failed to send OTP"}), 500

    # ✅ 4. Store OTP in Supabase
    try:
        otp_response = supabase.table("otp").insert({
            "email": email,
            "code": code,
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }).execute()

        return jsonify({"message": "OTP sent to your email"}), 200

    except Exception as e:
        print("❌ Error inserting OTP into Supabase:", e)
        return jsonify({"error": "Internal server error while saving OTP"}), 500


@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.form
    email = data.get("email")
    code = data.get("code")
    name = data.get("name")
    password = data.get("password")
    picture_file = request.files.get("picture")

    try:
        # 1. Get latest OTP
        response = supabase.table("otp").select("*").eq("email", email).order("expires_at", desc=True).limit(1).execute()
        otp = response.data

        if not otp:
            return jsonify({"error": "OTP not found"}), 400

        otp_record = otp[0]

        # ✅ FIX: Parse the date using strptime (microseconds included)
        try:
            expires_at = datetime.strptime(otp_record['expires_at'], "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            # fallback in case microseconds are missing
            expires_at = datetime.strptime(otp_record['expires_at'], "%Y-%m-%dT%H:%M:%S")

        if otp_record['code'] != code or expires_at < datetime.utcnow():
            return jsonify({"error": "Invalid or expired OTP"}), 400

        # 2. Check if user already exists
        user_check = supabase.table("user").select("*").eq("email", email).execute()
        if user_check.data:
            return jsonify({"error": "User already verified"}), 400

        # 3. Hash password
        hashed_password = generate_password_hash(password)

        # 4. Upload profile picture to Cloudinary
        picture_url = ""
        if picture_file:
            try:
                result = cloudinary.uploader.upload(picture_file)
                picture_url = result.get("secure_url", "")
            except Exception as e:
                print("Cloudinary error:", e)

        # 5. Insert user
        supabase.table("user").insert({
            "name": name,
            "email": email,
            "password": hashed_password,
            "is_verified": True,
            "picture_url": picture_url
        }).execute()

        # 6. Delete used OTPs
        supabase.table("otp").delete().eq("email", email).execute()

        return jsonify({"message": "Signup complete. You can now login."}), 201

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

# -------------------------------
# LOGIN
# -------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    response = supabase.table("user").select("*").eq("email", email).execute()
    users = response.data

    if not users:
        return jsonify({"error": "User not found"}), 404

    user = users[0]
    if not user.get("is_verified"):
        return jsonify({"error": "Please complete email verification first"}), 403

    if not check_password_hash(user.get("password", ""), password):
        return jsonify({"error": "Invalid password"}), 401

    access_token = create_access_token(identity=str(user["id"]))
    return jsonify({
        "token": access_token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role")
        }
    }), 200


# -------------------------------
# GET CURRENT USER
# -------------------------------
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    response = supabase.table("user").select("*").eq("id", user_id).execute()
    user = response.data[0] if response.data else None

    if user:
        return jsonify({
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role"),
            "picture_url": user.get("picture_url")
        })

    return jsonify({"error": "User not found"}), 404

# get user by id
@auth_bp.route("/user/<int:user_id>", methods=["GET"])
def get_user_by_id(user_id):
    try:
        response = supabase.table("user").select("id, name, email, role, picture_url").eq("id", user_id).single().execute()
        
        if response.data:
            return jsonify(response.data), 200
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        return jsonify({"error": "Failed to fetch user", "details": str(e)}), 500

# update profile route

@auth_bp.route("/update-profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.form
    name = data.get("name")
    password = data.get("password")
    picture_file = request.files.get("picture")

    update_data = {}

    # 🟡 Update name
    if name:
        update_data["name"] = name

    # 🔒 Update password
    if password:
        update_data["password"] = generate_password_hash(password)

    # 🖼️ Update profile picture
    if picture_file:
        try:
            result = cloudinary.uploader.upload(picture_file)
            update_data["picture_url"] = result.get("secure_url", "")
        except Exception as e:
            return jsonify({"error": "Image upload failed", "details": str(e)}), 500

    if not update_data:
        return jsonify({"error": "No data provided to update"}), 400

    try:
        supabase.table("user").update(update_data).eq("id", user_id).execute()
        return jsonify({"message": "Profile updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Profile update failed", "details": str(e)}), 500
