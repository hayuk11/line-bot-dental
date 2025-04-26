@app.route("/callback", methods=["POST"])
def callback():
    body = request.json

    for event in body.get("events", []):
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            print("🆔 USER ID:", user_id)  # <-- Adiciona isso!

            # O restante do seu código...
