from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN")

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        data = request.get_json()

        # เช็คก่อนว่ามี message และมี text หรือไม่
        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"]["text"]

            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": f"คุณพิมพ์ว่า: {text}"
            }

            requests.post(url, json=payload)

        return "OK"

    return "Bot is running"
