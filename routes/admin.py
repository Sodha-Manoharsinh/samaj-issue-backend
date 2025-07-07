from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from supabase import create_client
from config import Config

admin_bp = Blueprint("admin", __name__)
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# -------------------------------
# 🔐 Admin check helper
# -------------------------------
def is_admin(user_id):
    user = supabase.table("user").select("role").eq("id", user_id).single().execute()
    return user.data and user.data["role"] == "admin"

# -------------------------------
# GET /admin/flagged-comments
# -------------------------------
@admin_bp.route("/admin/flagged-comments", methods=["GET"])
@jwt_required()
def get_flagged_comments():
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({"error": "Unauthorized"}), 403

    res = supabase.table("comment").select("*").eq("is_flagged", True).order("created_at", desc=True).execute()
    return jsonify(res.data), 200

# -------------------------------
# GET /admin/stats
# -------------------------------
@admin_bp.route("/admin/stats", methods=["GET"])
@jwt_required()
def get_stats():
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        pending = supabase.table("issue").select("id", count="exact").eq("status", "Pending").execute()
        in_progress = supabase.table("issue").select("id", count="exact").eq("status", "In Progress").execute()
        resolved = supabase.table("issue").select("id", count="exact").eq("status", "Resolved").execute()

        return jsonify({
            "Pending": pending.count or 0,
            "In Progress": in_progress.count or 0,
            "Resolved": resolved.count or 0
        }), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch stats", "details": str(e)}), 500


# -------------------------------
# PUT /admin/issues/<id>/status
# -------------------------------
@admin_bp.route("/admin/issues/<int:issue_id>/status", methods=["PUT"])
@jwt_required()
def update_issue_status(issue_id):
    user_id = get_jwt_identity()
    if not is_admin(user_id):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    new_status = data.get("status")

    if new_status not in ["Pending", "In Progress", "Resolved"]:
        return jsonify({"error": "Invalid status"}), 400

    supabase.table("issue").update({"status": new_status}).eq("id", issue_id).execute()
    return jsonify({"message": f"Issue status updated to {new_status}"}), 200
