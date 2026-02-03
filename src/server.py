from flask import Flask, send_from_directory, Response
import os

app = Flask(__name__)

LOG_FILE = "vine_monitor.log"

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/log")
def log():
    if not os.path.exists(LOG_FILE):
        return Response("Log file not found", status=404)

    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()
    return Response(data, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3000, debug=False)