from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from routes.auth import auth_bp
from routes.issue import issue_bp
from routes.upvote import upvote_bp
from routes.comment import comment_bp
from routes.admin import admin_bp
from routes.summary import summary_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins="https://samaj-issue-frontend.vercel.app", supports_credentials=True)


# JWT setup
jwt = JWTManager(app)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/api")  # tested complete
app.register_blueprint(issue_bp, url_prefix="/api") # tested complete
app.register_blueprint(upvote_bp, url_prefix="/api") # tested complete
app.register_blueprint(comment_bp, url_prefix="/api") # tested complete
app.register_blueprint(admin_bp, url_prefix="/api") # tested complete
app.register_blueprint(summary_bp, url_prefix="/api") # tested complete

if __name__ == "__main__":
    app.run(debug=True)
