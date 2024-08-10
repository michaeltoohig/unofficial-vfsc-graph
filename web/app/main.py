import sys
from pathlib import Path

from flask import Flask, send_from_directory
from loguru import logger

from app.db.app_db import init_db as init_app_db, close_db as close_app_db
from app.db.graph_db import close_db as close_graph_db
from app.extensions import cache
from app.views.graph_view import graph_bp
from app.views.home_view import home_bp


def create_app():

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")

    setup_logging(app)
    setup_db(app)
    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    register_favicon(app)

    return app


def setup_logging(app):
    logger.remove()  # Remove the default handler
    # TODO: remove this color logging for production?
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    log_file = Path(app.config["LOGS_DIR"]) / "app.log"
    if not log_file.parent.exists():
        log_file.parent.mkdir(mode=744, parents=True)
    logger.add(str(log_file), rotation="50 MB")


def setup_db(app):
    data_dir = Path(app.config["DATA_DIR"])
    if not data_dir.exists():
        data_dir.mkdir(mode=744, parents=True)
    with app.app_context():
        init_app_db()
    app.teardown_appcontext(close_app_db)
    app.teardown_appcontext(close_graph_db)


def register_extensions(app):
    cache.init_app(app)


def register_blueprints(app):
    app.register_blueprint(home_bp)
    app.register_blueprint(graph_bp)


def register_errorhandlers(app):
    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        logger.exception(f"An unhandled exception occurred: {e}")
        return "An error occurred", 500


def register_favicon(app):
    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            app.static_folder,
            "icons/favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )


if __name__ == "__main__":
    app = create_app()
    # Only for debugging while developing
    app.run(host="0.0.0.0", debug=True, port=8080)
