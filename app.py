from flask import Flask, request
import os
import json
import sys

app = Flask(__name__)

@app.route("/")
def home():
    return "WEBHOOK DEBUG ACTIVE"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    sys.stdout.write("\n========== NEW UPDATE ==========\n")
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
    sys.stdout.write("\n================================\n")
    sys.stdout.flush()

    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
