from flask import Flask, request
import requests
import openai

app = Flask(__name__)

# 🔑 Sua chave da OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# 🔐 Seu Channel Access Token do LINE
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")

def reply_to_user(reply_token, messages):
    headers = {
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "replyToken": reply_token,
        "messages": messages
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=body)

def responder_com_ia(mensagem):
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente educado de uma clínica odontológica no Japão. Responda em japonês e de forma clara para pacientes."},
                {"role": "user", "content": mensagem}
            ]
        )
        return resposta.choices[0].message['content']
    except Exception as e:
        return "申し訳ありません。現在、システムが混雑しています。もう一度お試しください。"

@app.route("/callback", methods=["POST"])
def callback():
    body = request.json

    for event in body["events"]:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_message = event["message"]["text"]
            reply_token = event["replyToken"]

            if "予約" in user_message:
                reply_text = "ご予約ですね！お名前、希望日時、希望治療内容を教えてください。😊"
                reply_to_user(reply_token, [{"type": "text", "text": reply_text}])
            elif "質問" in user_message or "費用" in user_message or "痛み" in user_message:
                reply_text = "ご質問内容を選んでください：\n1️⃣ 歯痛について\n2️⃣ 費用について"
                reply_to_user(reply_token, [{"type": "text", "text": reply_text}])
            elif "1" == user_message:
                reply_text = "歯痛ですね。痛みの程度や場所を教えていただけますか？🦷"
                reply_to_user(reply_token, [{"type": "text", "text": reply_text}])
            elif "2" == user_message:
                reply_text = "費用についてですね。保険適用時は3割負担となります。💰"
                reply_to_user(reply_token, [{"type": "text", "text": reply_text}])
            else:
                resposta_ia = responder_com_ia(user_message)
                reply_to_user(reply_token, [{
                    "type": "text",
                    "text": resposta_ia,
                    "quickReply": {
                        "items": [
                            {
                                "type": "action",
                                "action": {
                                    "type": "message",
                                    "label": "📅 予約する",
                                    "text": "予約"
                                }
                            },
                            {
                                "type": "action",
                                "action": {
                                    "type": "message",
                                    "label": "❓ 質問する",
                                    "text": "質問"
                                }
                            }
                        ]
                    }
                }])
    return "OK"

if __name__ == "__main__":
    app.run(port=5000)
