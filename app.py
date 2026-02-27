from flask import Flask, request
import os
import json

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    print("\n========== NEW UPDATE ==========")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("================================\n")

    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
