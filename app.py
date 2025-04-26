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

# Estado dos pacientes para saber em que etapa estão
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

def gerar_resposta(mensagem_usuario, idioma):
    prompt = ""

    if idioma == "en":
        prompt = f"You are a polite receptionist AI for a dental clinic in Japan. Answer clearly in English. Patient message: "{mensagem_usuario}""
    elif idioma == "pt":
        prompt = f"Você é uma recepcionista educada de uma clínica odontológica no Japão. Responda claramente em português. Mensagem do paciente: "{mensagem_usuario}""
    else:
        prompt = f"あなたは日本の歯科クリニックの丁寧な受付AIです。次の患者のメッセージに日本語で回答してください："{mensagem_usuario}""

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

            if user_id not in user_languages:
                if user_message in ["日本語", "English", "Português", "Other"]:
                    if user_message == "日本語":
                        user_languages[user_id] = "ja"
                    elif user_message == "English":
                        user_languages[user_id] = "en"
                    elif user_message == "Português":
                        user_languages[user_id] = "pt"
                    else:
                        user_languages[user_id] = "ja"  # Default safe fallback
                    salvar_idiomas(user_languages)

                    # Depois que escolhe idioma, já avisa sobre necessidade de tsuyaku
                    aviso = mensagem_alerta_tsuyaku(user_languages[user_id])

                    reply_to_user(reply_token, [
                        {"type": "text", "text": "言語設定が完了しました。ご用件をどうぞ！😊"},
                        {"type": "text", "text": aviso}
                    ])

                    user_states[user_id] = "inicio"
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

                if user_message in ["予約", "Agendar", "Book"]:
                    user_states[user_id] = "nome"
                    reply_to_user(reply_token, [{"type": "text", "text": "Por favor, informe seu nome completo. 📝"}])
                elif estado == "nome":
                    user_states[user_id] = "data"
                    reply_to_user(reply_token, [{"type": "text", "text": "Qual a data e horário desejado? 📅 (ex: 6月10日15時)"}])
                elif estado == "data":
                    user_states[user_id] = "tratamento"
                    reply_to_user(reply_token, [{"type": "text", "text": "Qual o motivo da consulta? (ex: limpeza, dor de dente) 🦷"}])
                elif estado == "tratamento":
                    # Finalizando agendamento com alerta tsuyaku
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
