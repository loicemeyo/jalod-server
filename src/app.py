import os

from dotenv import load_dotenv

from flask import Flask
from flask_smorest import Api
from flask_jwt_extended import JWTManager

try:
    from .db import configure_database, db, ensure_member_auth_columns
    from .resources.auth import blp as AuthBlueprint
    from .resources.contributions import blp as ContributionBlueprint
    from .resources.members import blp as MemberBlueprint
    from .resources.treasury import blp as TreasuryBlueprint
    from .resources.welfare import blp as WelfareBlueprint
    from .schemas import ma
    from .models.welfare import WelfareModel
    from .models.contribution import ContributionModel
except ImportError:  # pragma: no cover - allows running app.py directly
    from db import configure_database, db, ensure_member_auth_columns
    from resources.auth import blp as AuthBlueprint
    from resources.contributions import blp as ContributionBlueprint
    from resources.members import blp as MemberBlueprint
    from resources.treasury import blp as TreasuryBlueprint
    from resources.welfare import blp as WelfareBlueprint
    from schemas import ma
    from models.welfare import WelfareModel
    from models.contribution import ContributionModel

# Ensure Flask-specific environment in `.flaskenv` is loaded during tests
# and when the app is created programmatically. Some environments (pytest)
# may not load .flaskenv automatically, so load it explicitly first.
load_dotenv(".flaskenv", override=True)
load_dotenv()

app = Flask(__name__)

app.config["PROPAGATE_EXCEPTIONS"] = True
app.config["API_TITLE"] = "Jalod Server API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/"
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")

configure_database(app)
ma.init_app(app)
api = Api(app)
api.register_blueprint(ContributionBlueprint)
api.register_blueprint(MemberBlueprint)
api.register_blueprint(AuthBlueprint)
api.register_blueprint(TreasuryBlueprint)
api.register_blueprint(WelfareBlueprint)

jwt = JWTManager(app)

with app.app_context():
    ensure_member_auth_columns(app)
    db.create_all()



@app.route("/")
def hello_world():
    return "Welcome to the Jalod Server App!"

if __name__ == "__main__":
    app.run(debug=True)