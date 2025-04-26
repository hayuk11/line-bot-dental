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
