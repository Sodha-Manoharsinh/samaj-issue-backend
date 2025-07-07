from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from supabase import create_client
from config import Config
import cloudinary

issue_bp = Blueprint("issue", __name__)

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# --------------------------------------
# GET /issues – Public list of all issues
# --------------------------------------
@issue_bp.route("/issues", methods=["GET"])
def get_issues():
    response = supabase.table("issue").select("*").order("created_at", desc=True).execute()
    return jsonify(response.data), 200

# ---------------------------------------------------
# GET /issues/<id> – Get full issue detail by ID
# ---------------------------------------------------
@issue_bp.route("/issues/<int:issue_id>", methods=["GET"])
def get_issue(issue_id):
    response = supabase.table("issue").select("*").eq("id", issue_id).execute()
    data = response.data
    if not data:
        return jsonify({"error": "Issue not found"}), 404
    return jsonify(data[0]), 200


# ---------------------------------------------------
# POST /new-issue – Create new issue (requires login)
# ---------------------------------------------------


@issue_bp.route("/new-issue", methods=["POST"])
@jwt_required()
def create_issue():
    user_id = get_jwt_identity()

    # Use form data (not JSON) because files can't be sent in JSON
    title = request.form.get("title")
    description = request.form.get("description")
    location = request.form.get("location")
    image_file = request.files.get("image")

    image_url = ""

    if image_file:
        try:
            upload_result = cloudinary.uploader.upload(image_file)
            image_url = upload_result.get("secure_url", "")
        except Exception as e:
            return jsonify({"error": "Image upload failed", "details": str(e)}), 500

    # Prepare data for Supabase insert
    issue_data = {
        "title": title,
        "description": description,
        "location": location,
        "image_url": image_url,
        "created_by": user_id
    }

    try:
        response = supabase.table("issue").insert(issue_data).execute()
        return jsonify({"message": "Issue posted successfully", "data": response.data}), 201
    except Exception as e:
        return jsonify({"error": "Database insert failed", "details": str(e)}), 500


# ---------------------------------------------------------
# PUT /issues/<id> – Update issue (creator or admin only)
# ---------------------------------------------------------

@issue_bp.route("/issues/<int:issue_id>", methods=["PUT"])
@jwt_required()
def update_issue(issue_id):
    user_id = get_jwt_identity()

    # ✅ Step 1: Get the issue safely
    try:
        issue_response = supabase.table("issue").select("*").eq("id", issue_id).execute()
        issue_data = issue_response.data
        if not issue_data:
            return jsonify({"error": "Issue not found"}), 404
        issue = issue_data[0]
    except Exception as e:
        return jsonify({"error": "Database error fetching issue", "details": str(e)}), 500

    # ✅ Step 2: Get the user and check role
    try:
        user_response = supabase.table("user").select("role").eq("id", user_id).execute()
        user_data = user_response.data
        if not user_data:
            return jsonify({"error": "User not found"}), 403
        user = user_data[0]
    except Exception as e:
        return jsonify({"error": "User fetch failed", "details": str(e)}), 500

    # ✅ Step 3: Check permission
    if str(issue["created_by"]) != str(user_id) and user["role"] != "admin":
        return jsonify({"error": "Unauthorized"}), 403


    # ✅ Step 4: Handle incoming form data (including image)
    title = request.form.get("title")
    description = request.form.get("description")
    location = request.form.get("location")
    image_file = request.files.get("image")

    image_url = issue.get("image_url", "")

    if image_file:
        try:
            upload_result = cloudinary.uploader.upload(image_file)
            image_url = upload_result.get("secure_url", image_url)
        except Exception as e:
            return jsonify({"error": "Image upload failed", "details": str(e)}), 500

    # ✅ Step 5: Build update data only from provided fields
    updated_data = {
        "title": title or issue["title"],
        "description": description or issue["description"],
        "location": location or issue["location"],
        "image_url": image_url
    }

    # ✅ Step 6: Submit the update
    try:
        update_response = supabase.table("issue").update(updated_data).eq("id", issue_id).execute()
        return jsonify({"message": "Issue updated", "data": update_response.data}), 200
    except Exception as e:
        return jsonify({"error": "Update failed", "details": str(e)}), 500


# ---------------------------------------------------------
# DELETE /issues/<id> – Delete issue (creator or admin only)
# ---------------------------------------------------------
@issue_bp.route("/issues/<int:issue_id>", methods=["DELETE"])
@jwt_required()
def delete_issue(issue_id):
    user_id = get_jwt_identity()

    # Fetch issue and user role
    issue_response = supabase.table("issue").select("*").eq("id", issue_id).single().execute()
    issue = issue_response.data
    user_response = supabase.table("user").select("role").eq("id", user_id).single().execute()
    user = user_response.data

    if not issue:
        return jsonify({"error": "Issue not found"}), 404

    if str(issue["created_by"]) != str(user_id) and user["role"] != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # 1. Delete related upvotes
        supabase.table("upvote").delete().eq("issue_id", issue_id).execute()

        # 2. Delete related comments (optional, if you have a comment table with issue_id FK)
        supabase.table("comment").delete().eq("issue_id", issue_id).execute()

        supabase.table("summary").delete().eq("issue_id", issue_id).execute()

        # 3. Delete issue
        supabase.table("issue").delete().eq("id", issue_id).execute()

        return jsonify({"message": "Issue deleted"}), 200

    except Exception as e:
        print("Delete issue error:", e)
        return jsonify({"error": "Failed to delete issue"}), 500

