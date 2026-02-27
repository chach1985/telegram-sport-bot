from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ====== ใส่ TOKEN ของคุณใน Render Environment ======
TOKEN = os.environ.get("TOKEN")

# ====== ปลายทางที่ 1 ======
GROUP_1 = -1003749819628
TOPIC_1 = 3

# ====== ปลายทางที่ 2 ======
GROUP_2 = -1003735613798
TOPIC_2 = 2


@app.route("/")
def home():
    return "Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data and "text" in data["message"]:
        text = data["message"]["text"]
        sender_name = data["message"]["from"].get("first_name", "Unknown")

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        message_text = f"📩 ข้อความจากทีม ({sender_name}):\n{text}"

        payload1 = {
            "chat_id": GROUP_1,
            "text": message_text,
            "message_thread_id": TOPIC_1
        }

        payload2 = {
            "chat_id": GROUP_2,
            "text": message_text,
            "message_thread_id": TOPIC_2
        }

        requests.post(url, json=payload1)
        requests.post(url, json=payload2)

    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
