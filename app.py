@app.route("/callback", methods=["POST"])
def callback():
    body = request.json

    for event in body["events"]:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            print("🪪 USER ID:", user_id)

            reply_token = event["replyToken"]
            reply_text = "Mensagem recebida ✅"
            send_message(reply_token, reply_text)

    return "OK"
