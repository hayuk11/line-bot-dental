import os
import requests
from flask import Flask, request, jsonify
from supabase import create_client
from datetime import datetime
import openai

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CLINIC_OWNER_USER_ID = os.getenv("CLINIC_LINE_USER_ID", "U7117f9979c27c0f5d46b328bc4e4f796")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

user_sessions = {}

base_times = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"
]

def send_line_message(reply_token, messages):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "replyToken": reply_token,
        "messages": messages
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=body)

def push_line_message(user_id, messages):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": user_id,
        "messages": messages
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=body)

def quick_reply(label):
    return {
        "type": "action",
        "action": {
            "type": "message",
            "label": label,
            "text": label
        }
    }

def cancelar_agendamento(user_id):
    supabase.table("Agendamentos").delete().eq("user_id", user_id).execute()

def horarios_disponiveis(data_escolhida):
    data = supabase.table("Agendamentos").select("*").execute()
    horarios_ocupados = [
        record["data_hora"].split(" ")[1]
        for record in data.data if record["data_hora"].startswith(data_escolhida)
    ]
    return [h for h in base_times if h not in horarios_ocupados]

@app.route("/callback", methods=["POST"])
def callback():
    body = request.json

    for event in body.get("events", []):
        if event["type"] != "message" or event["message"]["type"] != "text":
            continue

        user_id = event["source"]["userId"]
        user_message = event["message"]["text"]
        reply_token = event["replyToken"]
        session = user_sessions.get(user_id, {"step": "language"})

        if user_message.lower() == "meuid":
            send_line_message(reply_token, [{"type": "text", "text": f"Seu User ID é: {user_id}"}])
            return "OK"

        if session["step"] == "language":
            send_line_message(reply_token, [{
                "type": "text",
                "text": "🌐 Por favor, selecione seu idioma:",
                "quickReply": {
                    "items": [
                        quick_reply("🇯🇵 日本語"),
                        quick_reply("🇺🇸 English"),
                        quick_reply("🇧🇷 Português"),
                        quick_reply("🌏 Outro")
                    ]
                }
            }])
            session["step"] = "waiting_language"
            user_sessions[user_id] = session
            return "OK"

        if session["step"] == "waiting_language":
            session["language"] = user_message
            session["step"] = "japanese_status"
            send_line_message(reply_token, [{
                "type": "text",
                "text": "Você fala japonês fluentemente? 🇯🇵",
                "quickReply": {
                    "items": [
                        quick_reply("Sim"),
                        quick_reply("Não (vou trazer intérprete)"),
                        quick_reply("Não (não trarei intérprete)")
                    ]
                }
            }])
            user_sessions[user_id] = session
            return "OK"

        if session["step"] == "japanese_status":
            if user_message == "Não (não trarei intérprete)":
                session["status_japones"] = "Não trará intérprete"
                session["step"] = "confirm_translate_app"
                send_line_message(reply_token, [{
                    "type": "text",
                    "text": "Nossa clínica não possui intérprete. Você conseguirá se comunicar usando aplicativo de tradução? 📱",
                    "quickReply": {
                        "items": [
                            quick_reply("Sim, consigo"),
                            quick_reply("Não, não consigo")
                        ]
                    }
                }])
                user_sessions[user_id] = session
                return "OK"
            else:
                session["status_japones"] = user_message
                session["step"] = "collect_name"
                send_line_message(reply_token, [{"type": "text", "text": "Por favor, informe seu nome completo. ✍️"}])
                user_sessions[user_id] = session
                return "OK"

        if session["step"] == "confirm_translate_app":
            if user_message == "Sim, consigo":
                session["step"] = "collect_name"
                send_line_message(reply_token, [{"type": "text", "text": "Por favor, informe seu nome completo. ✍️"}])
            else:
                send_line_message(reply_token, [{"type": "text", "text": "Desculpe, mas através do chat não conseguiremos concluir seu agendamento devido à dificuldade com o idioma e à ausência de intérprete. Por favor, entre em contato diretamente com a clínica. ☎️"}])
                user_sessions.pop(user_id, None)
            return "OK"

        if session["step"] == "collect_name":
            session["nome"] = user_message
            session["step"] = "collect_date"
            send_line_message(reply_token, [{"type": "text", "text": "Por favor, informe o dia desejado (ex: 2025-05-20). 📅"}])
            user_sessions[user_id] = session
            return "OK"

        if session["step"] == "collect_date":
            session["date_selected"] = user_message
            disponiveis = horarios_disponiveis(session["date_selected"])
            if not disponiveis:
                send_line_message(reply_token, [{"type": "text", "text": "⚠️ Nenhum horário disponível para este dia. Por favor, escolha outro dia."}])
                session["step"] = "collect_date"
            else:
                session["step"] = "select_time"
                send_line_message(reply_token, [{
                    "type": "text",
                    "text": "🕒 Escolha um horário disponível:",
                    "quickReply": {
                        "items": [quick_reply(h) for h in disponiveis]
                    }
                }])
            user_sessions[user_id] = session
            return "OK"

        if session["step"] == "select_time":
            session["data_hora"] = f"{session['date_selected']} {user_message}"
            session["step"] = "collect_motivo"
            send_line_message(reply_token, [{"type": "text", "text": "Qual o motivo da consulta? 🦷"}])
            user_sessions[user_id] = session
            return "OK"

        if session["step"] == "collect_motivo":
            session["motivo"] = user_message
            session["step"] = "collect_telefone"
            send_line_message(reply_token, [{"type": "text", "text": "Por favor, informe seu telefone de contato. 📞"}])
            user_sessions[user_id] = session
            return "OK"

        if session["step"] == "collect_telefone":
            session["telefone"] = user_message

            supabase.table("Agendamentos").insert({
                "user_id": user_id,
                "nome": session.get("nome"),
                "data_hora": session.get("data_hora"),
                "motivo": session.get("motivo"),
                "telefone": session.get("telefone"),
                "idioma": session.get("language"),
                "status_japones": session.get("status_japones"),
                "criado_em": datetime.now().isoformat()
            }).execute()

            send_line_message(reply_token, [{"type": "text", "text": """✅ Sua consulta foi agendada com sucesso!

🕒 Horário de funcionamento da clínica: 09:00–12:00 / 14:00–18:00
📞 Caso haja qualquer alteração, entraremos em contato com você."""}])

            push_line_message(CLINIC_OWNER_USER_ID, [{
                "type": "template",
                "altText": "Novo agendamento recebido!",
                "template": {
                    "type": "confirm",
                    "text": f"Novo agendamento: ...",  # <– fecha a string com aspas

"text": f"🆕 Novo agendamento:\n\n👤 Nome: {nome}\n🗓️ Data/Hora: {data_hora}\n📋 Motivo: {motivo}\n🗣️ Idioma: {idioma}\n\nDeseja aceitar este agendamento?",
                    "actions": [
                        {
                            "type": "message",
                            "label": "✅ Aceitar",
                            "text": f"aceitar_{user_id}"
                        },
                        {
                            "type": "message",
                            "label": "❌ Recusar",
                            "text": f"recusar_{user_id}"
                        }
                    ]
                }
            }])

            user_sessions.pop(user_id, None)
            return "OK"

        if user_message.startswith("aceitar_"):
            send_line_message(reply_token, [{"type": "text", "text": "✅ Agendamento confirmado! Paciente será aguardado."}])
            return "OK"

        if user_message.startswith("recusar_"):
            uid = user_message.split("_")[1]
            cancelar_agendamento(uid)
            push_line_message(CLINIC_OWNER_USER_ID, [{"type": "text", "text": f"❌ O agendamento do paciente {uid} foi cancelado. Por favor, entre em contato com ele para explicar."}])
            return "OK"

    return jsonify({"status": "ok"})
