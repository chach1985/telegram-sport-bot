from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ====== IMPORTANT ======
TOKEN = os.environ.get("TOKEN")
GROUP_ID = -1003749819628
TOPIC_1 = 3
TOPIC_2 = 2
# =======================

@app.route("/")
def home():
    return "Bot is running."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Incoming update:", data)

    message = None

    if "message" in data:
        message = data["message"]
    elif "edited_message" in data:
        message = data["edited_message"]
    elif "channel_post" in data:
        message = data["channel_post"]

    if message and "text" in message:
        text = message["text"]
        sender_name = message.get("from", {}).get("first_name", "Unknown")

        message_text = f"📩 ข้อความจากทีม ({sender_name}):\n{text}"

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        payload1 = {
            "chat_id": GROUP_ID,
            "text": message_text,
            "message_thread_id": TOPIC_1
        }

        payload2 = {
            "chat_id": GROUP_ID,
            "text": message_text,
            "message_thread_id": TOPIC_2
        }

        r1 = requests.post(url, json=payload1)
        r2 = requests.post(url, json=payload2)

        print("Topic1:", r1.text)
        print("Topic2:", r2.text)

    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
