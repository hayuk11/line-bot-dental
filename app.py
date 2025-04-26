from flask import Flask, request
import requests

app = Flask(__name__)

# Coloque seu Channel Access Token aqui
CHANNEL_ACCESS_TOKEN = "SEU_ACCESS_TOKEN"

def reply_to_user(reply_token, messages):
    headers = {
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "replyToken": reply_token,
        "messages": messages
    }
    requests.post('https://api.line.me/v2/bot/message/reply', headers=headers, json=body)

@app.route("/callback", methods=['POST'])
def callback():
    body = request.json

    for event in body['events']:
        if event['type'] == 'message' and event['message']['type'] == 'text':
            user_message = event['message']['text']
            reply_token = event['replyToken']

            if "予約" in user_message:
                reply_text = "ご予約ですね！お名前、希望日時、希望治療内容を教えてください。😊"
            elif "質問" in user_message:
reply_text = "ご質問内容を選んでください：\n1️⃣ 歯痛について\n2️⃣ 費用について"
            elif "1" == user_message:
                reply_text = "歯痛ですね。痛みの程度や場所を教えていただけますか？🦷"
            elif "2" == user_message:
                reply_text = "費用についてですね。保険適用時は3割負担となります。💰"
            else:
                reply_text = "こんにちは！「予約」または「質問」と入力してください。📅"

            reply_to_user(reply_token, [{"type": "text", "text": reply_text}])

    return "OK"

if __name__ == "__main__":
    app.run(port=5000)
