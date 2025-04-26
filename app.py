from flask import Flask, request
import requests
import openai
import os
import json

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")

IDIOMA_FILE = "user_languages.json"

def carregar_idiomas():
    try:
        with open(IDIOMA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def salvar_idiomas(data):
    with open(IDIOMA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_languages = carregar_idiomas()
user_states = {}

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

def detectar_idioma(texto):
    texto = texto.lower()
    if "port" in texto:
        return "pt"
    elif "eng" in texto:
        return "en"
    elif "jap" in texto or "日本語" in texto:
        return "ja"
    else:
        return None

def saudacao_menu(idioma):
    if idioma == "pt":
        return "Como podemos ajudar?
1. Agendar consulta
2. Saber valores
3. Falar com atendente"
    elif idioma == "en":
        return "How can we help you?
1. Book an appointment
2. Price information
3. Talk to staff"
    else:
        return "ご用件をお知らせください。
1. 予約したい
2. 治療費を知りたい
3. スタッフと話したい"

def mensagem_alerta_tsuyaku(idioma):
    if idioma == "en":
        return "【Important Notice】\n\nOur clinic does not provide interpreter services.\nIf you are not fluent in Japanese, please bring an interpreter with you. 🔴"
    elif idioma == "pt":
        return "【Aviso Importante】\n\nNossa clínica não oferece serviço de intérprete.\nCaso não fale japonês fluente, será necessário trazer um intérprete. 🔴"
    else:
        return "【重要なお知らせ】\n\n当院では通訳者のご用意はございません。\n日本語での対応ができない場合、通訳の方の同伴が必要です。🔴"

@app.route("/callback", methods=["POST"])
def callback():
    global user_languages, user_states
    body = request.json

    for event in body["events"]:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_message = event["message"]["text"]
            reply_token = event["replyToken"]
            user_id = event["source"]["userId"]

            estado = user_states.get(user_id, "inicio")

            if user_id not in user_languages or estado == "esperando_idioma":
                if user_message in ["日本語", "English", "Português"]:
                    idioma = detectar_idioma(user_message)
                    user_languages[user_id] = idioma
                    salvar_idiomas(user_languages)
                    user_states[user_id] = "inicio"
                    aviso = mensagem_alerta_tsuyaku(idioma)
                    menu = saudacao_menu(idioma)
                    reply_to_user(reply_token, [
                        {"type": "text", "text": "Idioma configurado com sucesso!"},
                        {"type": "text", "text": aviso},
                        {"type": "text", "text": menu}
                    ])
                elif user_message == "Other":
                    user_states[user_id] = "esperando_idioma"
                    reply_to_user(reply_token, [{"type": "text", "text": "Please type your preferred language (e.g., English, Vietnamese, Tagalog...)"}])
                else:
                    idioma_detectado = detectar_idioma(user_message)
                    if estado == "esperando_idioma" and idioma_detectado:
                        user_languages[user_id] = idioma_detectado
                        salvar_idiomas(user_languages)
                        user_states[user_id] = "inicio"
                        aviso = mensagem_alerta_tsuyaku(idioma_detectado)
                        menu = saudacao_menu(idioma_detectado)
                        reply_to_user(reply_token, [
                            {"type": "text", "text": "Language saved!"},
                            {"type": "text", "text": aviso},
                            {"type": "text", "text": menu}
                        ])
                    else:
                        reply_to_user(reply_token, [{
                            "type": "text",
                            "text": "こんにちは！Please select your preferred language 🌐",
                            "quickReply": {
                                "items": [
                                    {"type": "action", "action": {"type": "message", "label": "🇯🇵 日本語", "text": "日本語"}},
                                    {"type": "action", "action": {"type": "message", "label": "🇺🇸 English", "text": "English"}},
                                    {"type": "action", "action": {"type": "message", "label": "🇧🇷 Português", "text": "Português"}},
                                    {"type": "action", "action": {"type": "message", "label": "🌐 Other", "text": "Other"}}
                                ]
                            }
                        }])
            else:
                idioma = user_languages[user_id]
                estado = user_states.get(user_id, "inicio")

                resposta = saudacao_menu(idioma) if user_message in ["1", "2", "3"] else user_message
                reply_to_user(reply_token, [{"type": "text", "text": resposta}])

    return "OK"

if __name__ == "__main__":
    app.run(port=5000)
