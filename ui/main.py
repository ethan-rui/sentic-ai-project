from flask import Flask, url_for
import os
from flask.templating import render_template

BASEDIR = os.getcwd()


app = Flask(
    __name__, template_folder=f"{BASEDIR}/templates", static_folder=f"{BASEDIR}/static"
)

app.config["SECRET_KEY"] = "1234"


@app.route("/")
def page_home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
