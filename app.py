from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ดึง TOKEN จาก Environment Variable
TOKEN = os.environ.get("TOKEN")

# ====== ตั้งค่ากลุ่ม ======
GROUP_ID = -1003749819628

# Topic IDs
TOPIC_1 = 3   # สเตเดี้ยม 1
TOPIC_2 = 2   # สเตเดี้ยม 2
# ===========================


@app.route("/")
def home():
    return "Telegram Bot is running."


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    # ตรวจสอบว่ามีข้อความเข้ามา
    if "message" in data and "text" in data["message"]:
        text = data["message"]["text"]
        sender_name = data["message"]["from"].get("first_name", "Unknown")

        message_text = f"📩 ข้อความจากทีม ({sender_name}):\n{text}"

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        # ส่งเข้า Topic 1
        payload1 = {
            "chat_id": GROUP_ID,
            "text": message_text,
            "message_thread_id": TOPIC_1
        }

        # ส่งเข้า Topic 2
        payload2 = {
            "chat_id": GROUP_ID,
            "text": message_text,
            "message_thread_id": TOPIC_2
        }

        r1 = requests.post(url, json=payload1)
        r2 = requests.post(url, json=payload2)

        print("Topic 1 response:", r1.text)
        print("Topic 2 response:", r2.text)

    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
