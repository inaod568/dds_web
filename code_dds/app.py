"Web app template."

# IMPORTS ########################################################### IMPORTS #

# Standard library

# Installed
from flask import (Flask, g, redirect, render_template, request, url_for)
import jinja2
import mariadb

# Own modules
from code_dds import constants
from code_dds import utils

import code_dds.about
import code_dds.config
import code_dds.user
import code_dds.site

import code_dds.api.about
import code_dds.api.root
import code_dds.api.schema
import code_dds.api.user

# CONFIG ############################################################# CONFIG #

app = Flask(__name__)

# URL map converters - "xxx" will result in that xxx can be used in @app.route
app.url_map.converters["name"] = utils.NameConverter
app.url_map.converters["iuid"] = utils.IuidConverter

# Get and initialize app configuration
code_dds.config.init(app)
# utils.init(app)
# code_dds.user.init(app)
# utils.mail.init_app(app)

# Add template filters - "converts" integers with thousands delimiters
app.add_template_filter(utils.thousands)


# Context processors injects new variables automatically into the context of a
# template. Runs before the template is rendered.
# Returns a dictionary. Keys and values are merged with the template context
# for all templates in the app. In this case: the constants and the function
# csrf_token.
@app.context_processor
def setup_template_context():
    "Add useful stuff to the global context of Jinja2 templates."
    return dict(constants=constants,
                csrf_token=utils.csrf_token)


# Registers a function to run before >>each<< request
@app.before_request
def prepare():
    "Open the database connection; get the current user."
    g.db = mariadb.connect(**app.config['DB'])
    g.current_user = "tester"
    # flask.g.db = utils.get_db()
    # flask.g.current_user = webapp.user.get_current_user()
    # flask.g.am_admin = flask.g.current_user and \
    #     flask.g.current_user["role"] == constants.ADMIN


# app.after_request(utils.log_access)


@app.route("/")
def home():
    """Home page."""
    return render_template("home.html")


# @app.route('/login')
# def login():
#     """Login"""
#     return render_template('home.html')
    
# @app.route("/debug")
# @utils.admin_required
# def debug():
#     "Return some debug info for admin."
#     result = [f"<h1>Debug  {constants.VERSION}</h2>"]
#     result.append("<h2>headers</h2>")
#     result.append("<table>")
#     for key, value in sorted(request.headers.items()):
#         result.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
#     result.append("</table>")
#     result.append("<h2>environ</h2>")
#     result.append("<table>")
#     for key, value in sorted(request.environ.items()):
#         result.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
#     result.append("</table>")
#     return jinja2.utils.Markup("\n".join(result))


# Set up the URL map.
# app.register_blueprint(code_dds.about.blueprint, url_prefix="/about")
app.register_blueprint(code_dds.user.blueprint, url_prefix="/user")
# app.register_blueprint(code_dds.site.blueprint, url_prefix="/site")
# To be developed.
# app.register_blueprint(code_dds.entity.blueprint, url_prefix="/entity")

# app.register_blueprint(code_dds.api.root.blueprint, url_prefix="/api")
# app.register_blueprint(code_dds.api.about.blueprint, url_prefix="/api/about")
# app.register_blueprint(code_dds.api.schema.blueprint, url_prefix="/api/schema")
# app.register_blueprint(code_dds.api.user.blueprint, url_prefix="/api/user")
# To be developed
# app.register_blueprint(code_dds.api.entity.blueprint, url_prefix="/api/entity")


# This code is used only during development.
if __name__ == "__main__":
    app.run(host=app.config["SERVER_HOST"],
            port=app.config["SERVER_PORT"])