from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from supabase import create_client
from config import Config

upvote_bp = Blueprint("upvote", __name__)
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# ----------------------------------------------------
# POST /issues/<id>/upvote – Toggle upvote for issue
# ----------------------------------------------------
@upvote_bp.route("/issues/<int:issue_id>/upvote", methods=["POST"])
@jwt_required()
def toggle_upvote(issue_id):
    user_id = get_jwt_identity()

    try:
        # Check if upvote already exists
        existing = supabase.table("upvote").select("id").eq("user_id", user_id).eq("issue_id", issue_id).execute()

        if existing.data:
            # Remove upvote
            supabase.table("upvote").delete().eq("user_id", user_id).eq("issue_id", issue_id).execute()
            return jsonify({"message": "Upvote removed"}), 200
        else:
            # Add upvote
            supabase.table("upvote").insert({
                "user_id": user_id,
                "issue_id": issue_id
            }).execute()
            return jsonify({"message": "Upvoted"}), 201

    except Exception as e:
        return jsonify({"error": "Failed to toggle upvote", "details": str(e)}), 500


# ---------------------------------------------------------
# GET /issues/<id>/upvotes – Get count & user status
# ---------------------------------------------------------
@upvote_bp.route("/issues/<int:issue_id>/upvotes", methods=["GET"])
@jwt_required(optional=True)
def get_upvotes(issue_id):
    user_id = get_jwt_identity()

    try:
        # Total upvotes
        response = supabase.table("upvote").select("id", count="exact").eq("issue_id", issue_id).execute()
        total = response.count or 0

        # Check if this user has upvoted
        has_upvoted = False
        if user_id:
            check = supabase.table("upvote").select("id").eq("user_id", user_id).eq("issue_id", issue_id).execute()
            has_upvoted = bool(check.data)

        return jsonify({
            "issue_id": issue_id,
            "total_upvotes": total,
            "has_upvoted": has_upvoted
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch upvotes", "details": str(e)}), 500
