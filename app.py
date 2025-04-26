import os
import requests
from flask import Flask, request, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta
import openai

# Variáveis de ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

user_sessions = {}

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

def push_message_to_clinic(user_message):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    clinic_user_id = os.getenv("CLINIC_LINE_USER_ID")
    body = {
        "to": clinic_user_id,
        "messages": [{"type": "text", "text": user_message}]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=body)

def available_times(date_selected):
    base_times = [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"
    ]
    data = supabase.table("Agendamentos").select("*").eq("data_hora", date_selected).execute()
    booked_times = [record["data_hora"].split(" ")[1] for record in data.data if date_selected in record["data_hora"]]
    return [t for t in base_times if t not in booked_times]

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

        if session["step"] == "language":
            send_line_message(reply_token, [{
                "type": "text",
                "text": "🌐 Please select your language:",
                "quickReply": {
                    "items": [
                        quick_reply("🇯🇵 日本語"),
                        quick_reply("🇺🇸 English"),
                        quick_reply("🇧🇷 Português"),
                        quick_reply("🌏 Other")
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
                    "text": "Nossa clínica não possui intérprete. Você consegue se comunicar sozinho ou usando aplicativo de tradução? 📱",
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
                send_line_message(reply_token, [{"type": "text", "text": "Desculpe, mas através do chat não conseguiremos concluir seu agendamento devido à dificuldade com o idioma e à ausência de intérprete.

Por favor, entre em contato diretamente com a clínica para mais informações. ☎️"}])
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
            times = available_times(session["date_selected"])
            if not times:
                send_line_message(reply_token, [{"type": "text", "text": "Não temos horários disponíveis neste dia. Por favor, escolha outra data. 🙏"}])
                session["step"] = "collect_date"
            else:
                session["step"] = "select_time"
                send_line_message(reply_token, [{
                    "type": "text",
                    "text": "Escolha um horário disponível:",
                    "quickReply": {
                        "items": [quick_reply(t) for t in times]
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

            # Salvar no Supabase
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

            # Mensagem automática pro paciente
            send_line_message(reply_token, [{"type": "text", "text": "✅ Sua solicitação foi recebida! Em breve a clínica confirmará com você. Obrigado!"}])

            # Mensagem automática pro LINE da clínica
            msg = f"📢 Novo agendamento:

Nome: {session.get('nome')}
Data/Hora: {session.get('data_hora')}
Motivo: {session.get('motivo')}
Telefone: {session.get('telefone')}
Idioma: {session.get('language')}
Situação Japonês: {session.get('status_japones')}"
            push_message_to_clinic(msg)

            user_sessions.pop(user_id, None)
            return "OK"

    return jsonify({"status": "ok"})

def quick_reply(label):
    return {
        "type": "action",
        "action": {
            "type": "message",
            "label": label,
            "text": label
        }
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
