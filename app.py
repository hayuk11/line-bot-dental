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

def gerar_resposta(mensagem_usuario, idioma):
    if idioma == "en":
        prompt = f"You are a polite receptionist AI for a dental clinic in Japan. Answer clearly in English. Patient message: '{mensagem_usuario}'"
    elif idioma == "pt":
        prompt = f"Você é uma recepcionista educada de uma clínica odontológica no Japão. Responda claramente em português. Mensagem do paciente: '{mensagem_usuario}'"
    else:
        prompt = f"あなたは日本の歯科クリニックの丁寧な受付AIです。次の患者のメッセージに日本語で回答してください：'{mensagem_usuario}'"

    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}]
        )
        return resposta.choices[0].message['content']
    except:
        return "申し訳ありません。現在、システムが混雑しています。後ほどお試しください。"

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
                    if user_message == "日本語":
                        idioma = "ja"
                    elif user_message == "English":
                        idioma = "en"
                    elif user_message == "Português":
                        idioma = "pt"

                    user_languages[user_id] = idioma
                    salvar_idiomas(user_languages)
                    user_states[user_id] = "inicio"

                    aviso = mensagem_alerta_tsuyaku(idioma)
                    reply_to_user(reply_token, [
                        {"type": "text", "text": "言語設定が完了しました。ご用件をどうぞ！😊"},
                        {"type": "text", "text": aviso}
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
                        reply_to_user(reply_token, [
                            {"type": "text", "text": "Language saved! You can now start your consultation."},
                            {"type": "text", "text": aviso}
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

                if user_message.lower() in ["予約", "agendar", "book"]:
                    user_states[user_id] = "nome"
                    reply_to_user(reply_token, [{"type": "text", "text": "Por favor, informe seu nome completo. 📝"}])
                elif estado == "nome":
                    user_states[user_id] = "data"
                    reply_to_user(reply_token, [{"type": "text", "text": "Qual a data e horário desejado? 📅 (ex: 6月10日15時)"}])
                elif estado == "data":
                    user_states[user_id] = "tratamento"
                    reply_to_user(reply_token, [{"type": "text", "text": "Qual o motivo da consulta? (ex: limpeza, dor de dente) 🦷"}])
                elif estado == "tratamento":
                    aviso = mensagem_alerta_tsuyaku(idioma)
                    reply_to_user(reply_token, [
                        {"type": "text", "text": "ご予約内容を承りました！ありがとうございました。😊"},
                        {"type": "text", "text": aviso}
                    ])
                    user_states[user_id] = "inicio"
                else:
                    resposta = gerar_resposta(user_message, idioma)
                    reply_to_user(reply_token, [{"type": "text", "text": resposta}])

    return "OK"

if __name__ == "__main__":
    app.run(port=5000)
