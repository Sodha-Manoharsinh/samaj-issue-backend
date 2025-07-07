from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from supabase import create_client
from config import Config

comment_bp = Blueprint("comment", __name__)
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# ------------------------------
# GET: All Comments for an Issue
# ------------------------------
@comment_bp.route("/issues/<int:issue_id>/comments", methods=["GET"])
def get_comments(issue_id):
    try:
        res = supabase.table("comment").select("id, text, created_at, user_id, user(id, name, picture_url)").eq("issue_id", issue_id).order("created_at", desc=True).execute()

        return jsonify(res.data), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch comments", "details": str(e)}), 500


# ------------------------------
# POST: Add Comment to Issue
# ------------------------------
@comment_bp.route("/issues/<int:issue_id>/add-comment", methods=["POST"])
@jwt_required()
def add_comment(issue_id):
    user_id = get_jwt_identity()
    data = request.json
    text = data.get("text")

    if not text:
        return jsonify({"error": "Comment text is required"}), 400

    try:
        supabase.table("comment").insert({
            "text": text,
            "user_id": user_id,
            "issue_id": issue_id,
            "is_flagged": False  # Default is not flagged
        }).execute()
        return jsonify({"message": "Comment added", "flagged": False}), 201
    except Exception as e:
        return jsonify({"error": "Failed to add comment", "details": str(e)}), 500


# ------------------------------
# PUT: Update Comment (Owner or Admin)
# ------------------------------
@comment_bp.route("/comments/<int:comment_id>", methods=["PUT"])
@jwt_required()
def update_comment(comment_id):
    user_id = get_jwt_identity()
    data = request.json
    new_text = data.get("text", "").strip()

    if not new_text:
        return jsonify({"error": "Comment text is required"}), 400

    try:
        # Fetch comment to check ownership
        comment_res = supabase.table("comment").select("id", "user_id").eq("id", comment_id).single().execute()
        if not comment_res.data:
            return jsonify({"error": "Comment not found"}), 404

        comment = comment_res.data

        # Fetch user to check role
        user_res = supabase.table("user").select("role").eq("id", user_id).single().execute()
        role = user_res.data["role"] if user_res.data else "user"

        if str(comment["user_id"]) != str(user_id) and role != "admin":
            return jsonify({"error": "Unauthorized"}), 403

        # Perform update
        supabase.table("comment").update({"text": new_text}).eq("id", comment_id).execute()
        return jsonify({"message": "Comment updated"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to update comment", "details": str(e)}), 500


# ------------------------------
# DELETE: Comment (Owner or Admin)
# ------------------------------
@comment_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment(comment_id):
    user_id = get_jwt_identity()

    try:
        comment = supabase.table("comment").select("id", "user_id").eq("id", comment_id).single().execute()
        if not comment.data:
            return jsonify({"error": "Comment not found"}), 404

        user = supabase.table("user").select("role").eq("id", user_id).single().execute()
        is_admin = user.data["role"] == "admin"

        if str(comment.data["user_id"]) != str(user_id) and not is_admin:
            return jsonify({"error": "Unauthorized"}), 403

        supabase.table("comment").delete().eq("id", comment_id).execute()
        return jsonify({"message": "Comment deleted"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to delete comment", "details": str(e)}), 500


# ------------------------------
# PUT: Flag Comment (Admin Only)
# ------------------------------
@comment_bp.route("/comments/<int:comment_id>/flag", methods=["PUT"])
@jwt_required()
def flag_comment(comment_id):
    user_id = get_jwt_identity()

    try:
        user = supabase.table("user").select("role").eq("id", user_id).single().execute()
        if not user.data or user.data["role"] != "admin":
            return jsonify({"error": "Only admin can flag comments"}), 403

        response = supabase.table("comment").update({"is_flagged": True}).eq("id", comment_id).execute()
        print(response.data)
        if not response.data:
            return jsonify({"error": "Comment not found"}), 403
        
        return jsonify({"message": "Comment flagged"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to flag comment", "details": str(e)}), 500
