import os
import json
import logging
from aiohttp import web, ClientSession

BOT_TOKEN = "8345829799:AAE3Mi4q-gmscsxjCcCJnYKukGuMYFdcbpU"
ADMIN_ID = 7040587293
USERS_FILE = "users_db.json"
MAINTENANCE_TEXT = (
    "⚙️ <b>Бот на техническом перерыве</b>\n\n"
    "Наша команда прямо сейчас внедряет новые функции и исправляет баги, "
    "чтобы сделать сервис еще лучше.\n\n"
    "Скоро мы вернемся в строй! Спасибо за терпение."
)

logging.basicConfig(level=logging.INFO)
routes = web.RouteTableDef()

async def send_message(session, chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with session.post(url, json=payload) as response:
            result = await response.json()
            if not result.get("ok"):
                logging.error(f"❌ Ошибка Telegram API для {chat_id}: {result}")
            else:
                logging.info(f"✅ Сообщение отправлено {chat_id}")
            return result
    except Exception as e:
        logging.error(f"❌ Ошибка сети при отправке {chat_id}: {e}")
        return None

@routes.get("/")
async def root_handler(request):
    return web.Response(text="Microservice is running correctly!", status=200)

@routes.post("/sync")
async def sync_handler(request):
    try:
        data = await request.json()
        users = data.get("users", [])
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        logging.info(f"📥 Синхронизация базы: {len(users)} пользователей")
        return web.Response(text="Synced", status=200)
    except Exception as e:
        logging.error(f"❌ Ошибка синхронизации: {e}")
        return web.Response(text=str(e), status=500)

@routes.post("/webhook")
async def webhook_handler(request):
    try:
        data = await request.json()
        # Логируем входящий апдейт, чтобы видеть, что Телеграм вообще долбится к нам
        logging.info(f"📨 Получен апдейт: {json.dumps(data)}")

        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            text = msg.get("text", "")

            async with ClientSession() as session:
                # 1. Логика админа
                if user_id == ADMIN_ID and text.startswith("/broadcast "):
                    broadcast_msg = text.replace("/broadcast ", "")
                    targets = []
                    if os.path.exists(USERS_FILE):
                        with open(USERS_FILE, "r") as f:
                            targets = json.load(f)
                    
                    count = 0
                    for target_id in targets:
                        res = await send_message(session, target_id, broadcast_msg)
                        if res and res.get("ok"):
                            count += 1
                    
                    await send_message(session, ADMIN_ID, f"📢 Рассылка завершена: {count} получено")
                
                elif user_id == ADMIN_ID and text == "/status":
                    await send_message(session, ADMIN_ID, "🟢 Микросервис активен.")

                # 2. Логика для ВСЕХ остальных (заглушка)
                # Убрали else, чтобы админ тоже мог видеть заглушку, если пишет не команду
                elif user_id != ADMIN_ID: 
                    await send_message(session, chat_id, MAINTENANCE_TEXT)

    except Exception as e:
        logging.error(f"❌ Критическая ошибка в вебхуке: {e}")
    
    return web.Response(status=200)

app = web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
