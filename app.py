from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Pegando o token do ambiente (configure no Render como LINE_CHANNEL_ACCESS_TOKEN)
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

def send_message(reply_token, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "text",
            "text": text
        }]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=body)

@app.route("/callback", methods=["POST"])
def callback():
    body = request.json

    for event in body["events"]:
    if event["type"] == "message" and event["message"]["type"] == "text":
        user_id = event["source"]["userId"]
        print("🆔 USER ID:", user_id)

            # Aqui pode entrar lógica para processar o texto do usuário
            reply_text = "Mensagem recebida ✅"

            send_message(reply_token, reply_text)

    return "OK"
