@app.route("/callback", methods=["POST"])
def callback():
    body = request.json

    for event in body["events"]:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_message = event["message"]["text"]
            reply_token = event["replyToken"]

            # aqui vai sua lógica para processar a mensagem
            # exemplo:
            reply_text = "Mensagem recebida ✅"

            send_message(reply_token, reply_text)

    return "OK"
user_id = event["source"]["userId"]
user_message = event["message"]["text"]
reply_token = event["replyToken"]

# --- Novo código para mostrar o userId
if user_message.lower() == "meuid":
    send_line_message(reply_token, [{
        "type": "text",
        "text": f"Seu userId é: {user_id}"
    }])
    return "OK"
# --- Fim do novo código
