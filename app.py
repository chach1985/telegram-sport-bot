from flask import Flask, request
import sys
import json

app = Flask(__name__)

@app.route("/")
def home():
    return "WEBHOOK DEBUG MODE ACTIVE"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    print("========== NEW TELEGRAM UPDATE ==========", flush=True)
    print(json.dumps(data, indent=2), flush=True)
    print("=========================================", flush=True)

    sys.stdout.flush()

    return "OK", 200

if __name__ == "__main__":
    app.run()
