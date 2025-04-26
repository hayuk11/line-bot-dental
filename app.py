from flask import Flask, request
import requests
import openai
import os

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")

# Memória de idiomas por userId
user_languages = {}

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

def detectar_idioma_com_openai(mensagem_usuario):
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Detecte o idioma da seguinte frase. Responda apenas com 'ja', 'en', 'pt' ou 'outro'."},
                {"role": "user", "content": mensagem_usuario}
            ]
        )
        idioma_detectado = resposta.choices[0].message['content'].strip().lower()
        if idioma_detectado not in ["ja", "en", "pt"]:
            idioma_detectado = "ja"
        return idioma_detectado
    except:
        return "ja"

def gerar_resposta_com_ia(idioma, mensagem_usuario):
    prompt = ""

    if idioma == "en":
        prompt = f"""
You are a polite receptionist AI for a dental clinic in Japan.
Answer clearly in English. The patient's message is: "{mensagem_usuario}"
"""
    elif idioma == "pt":
        prompt = f"""
Você é uma recepcionista educada de uma clínica odontológica no Japão.
Responda em português claro. A mensagem do paciente é: "{mensagem_usuario}"
"""
    else:  # padrão japonês
        prompt = f"""
あなたは日本の歯科クリニックの丁寧な受付AIです。
以下の患者さんのメッセージに対して、日本語で丁寧に回答してください："{mensagem_usuario}"
"""

    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt}
            ]
        )
        return resposta.choices[0].message['content']
    except:
        return "申し訳ありません。現在、システムが混雑しています。後ほどお試しください。"

@app.route("/callback", methods=["POST"])
def callback():
    body = request.json

    for event in body["events"]:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_message = event["message"]["text"]
            reply_token = event["replyToken"]
            user_id = event["source"]["userId"]

            # Quick replies para comandos fixos
            if "予約" in user_message:
                reply_text = "ご予約ですね！お名前、希望日時、希望治療内容を教えてください。😊"
                reply_to_user(reply_token, [{"type": "text", "text": reply_text}])
            elif "質問" in user_message:
                reply_text = "ご質問内容を選んでください：\n1️⃣ 歯痛について\n2️⃣ 費用について"
                reply_to_user(reply_token, [{"type": "text", "text": reply_text}])
            elif "1" == user_message:
                reply_text = "歯痛ですね。痛みの程度や場所を教えていただけますか？🦷"
                reply_to_user(reply_token, [{"type": "text", "text": reply_text}])
            elif "2" == user_message:
                reply_text = "費用についてですね。保険適用時は3割負担となります。💰"
                reply_to_user(reply_token, [{"type": "text", "text": reply_text}])
            else:
                # Inteligência para idioma
                if user_id not in user_languages:
                    idioma_detectado = detectar_idioma_com_openai(user_message)
                    user_languages[user_id] = idioma_detectado
                else:
                    idioma_detectado = user_languages[user_id]

                resposta = gerar_resposta_com_ia(idioma_detectado, user_message)

                reply_to_user(reply_token, [{
                    "type": "text",
                    "text": resposta,
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
