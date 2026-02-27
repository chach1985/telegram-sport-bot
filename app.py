from flask import Flask, request
import os
import json

app = Flask(__name__)

# ====== HOME ROUTE (ใช้เช็คว่า Deploy สำเร็จหรือยัง) ======
@app.route("/")
def home():
    return "BOT VERSION 2 - WEBHOOK DEBUG MODE"

# ====== WEBHOOK ROUTE ======
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    print("\n========== NEW UPDATE ==========")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("================================\n")

    return "OK"

# ====== RUN SERVER ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
