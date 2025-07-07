from flask import Blueprint, jsonify
from supabase import create_client
from config import Config
import cohere

summary_bp = Blueprint("summary", __name__)
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

co = cohere.Client(Config.COHERE_API_KEY)


@summary_bp.route("/issues/<int:issue_id>/summary", methods=["GET"])
def get_summary(issue_id):
    # ✅ Step 1: Get issue and comments
    try:
        issue_res = supabase.table("issue").select("title, description").eq("id", issue_id).single().execute()
        comment_res = supabase.table("comment").select("text").eq("issue_id", issue_id).execute()

        if not issue_res.data:
            return jsonify({"error": "Issue not found"}), 404

        issue = issue_res.data
        comments = comment_res.data or []

        combined_text = f"Issue: {issue['title']}\nDescription: {issue['description']}\n\nComments:\n"
        combined_text += "\n".join([c["text"] for c in comments])
    except Exception as e:
        return jsonify({"error": "Failed to fetch issue or comments", "details": str(e)}), 500

    # ✅ Step 2.5: Add fallback filler text if too short
    if len(combined_text) < 250:
        filler = f"""This is a discussion around a community issue titled: "{issue['title']}".\n\n"""
        filler += f"Description: {issue['description']}\nkdlsj; f;kjdjffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff\nCommunity Comments:\n"
        if comments:
            for c in comments:
                filler += f"- {c['text']}\n"
        else:
            filler += "- No comments have been added yet.\n"
        combined_text = filler

    if len(combined_text) < 250:
        return jsonify({"error": "Not enough content to summarize. Add more description or comments."}), 400

    # ✅ Step 3: Generate summary with Cohere
    try:
        response = co.summarize(
            text=combined_text,
            length='long',
            format='paragraph'
        )
        summary_text = response.summary.strip()
    except Exception as e:
        return jsonify({"error": "Cohere summarization failed", "details": str(e)}), 500

    # ✅ Step 4: Save the summary
    try:
        saved = supabase.table("summary").insert({
            "text": summary_text,
            "issue_id": issue_id
        }).execute()
        return jsonify(saved.data[0]), 200
    except Exception as e:
        return jsonify({"error": "Failed to save summary", "details": str(e)}), 500
