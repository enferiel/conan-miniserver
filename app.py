import flask
import yaml
import pathlib
import waitress

import activity

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

PASSWORD = config["password"]
HOST = config["host"]
PORT = config["port"]
SECRET_KEY = config["secret_key"]
DB_PATH = pathlib.Path(config["db_path"])

if not DB_PATH.exists():
    raise RuntimeError(f"DB_PATH does not exist: {DB_PATH}")

app = flask.Flask(__name__)
app.secret_key = SECRET_KEY

data: list[tuple[str, float]] | None = None
threshold: float = 8


def format_time(seconds: float):
    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or len(time_parts) == 0:
        time_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return ", ".join(time_parts)


def get_data():
    logs = activity.parse_logs(DB_PATH)
    durations = activity.Log.get_total_durations(logs)

    global data
    data = []
    for player, duration in durations.items():
        data.append((player, duration))

    data.sort(key=lambda row: row[1])
    data = [(row[0], format_time(row[1]), row[1]) for row in data]

    return data


@app.route("/", methods=["GET"])
def index():
    if "logged_in" in flask.session:
        global data
        data = get_data()
        return flask.render_template("main.html", threshold=threshold, data=data)
    return flask.render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    password = flask.request.form.get("password")
    if password == PASSWORD:
        flask.session["logged_in"] = True
        return flask.redirect(flask.url_for("index"))
    return flask.render_template("login.html", error="Incorrect password!")


@app.route("/logout", methods=["POST"])
def logout():
    flask.session.pop("logged_in", None)
    return flask.redirect(flask.url_for("index"))


@app.route("/refresh", methods=["POST"])
def refresh():
    global threshold
    new_threshold = flask.request.form.get("threshold", type=float)
    threshold = new_threshold
    return flask.redirect(flask.url_for("index"))


if __name__ == "__main__":
    waitress.serve(app, host=HOST, port=PORT)
