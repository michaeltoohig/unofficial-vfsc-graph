from flask import Flask, g, redirect, request, url_for
from app.home import home_bp

from app.graph import graph_bp


def create_app():

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")

    register_blueprints(app)
    register_favicon(app)

    return app


def register_blueprints(app):
    app.register_blueprint(home_bp)
    app.register_blueprint(graph_bp)


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
