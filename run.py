from highrise.__main__ import *
import time
import traceback

bot_file_name = "main"
bot_class_name = "Bot"
room_id2 = "6644b8d5532cace4f8103f59"
bot_token2 = "fb7708a87a840e9f6d036271e38b96272ac25e7b91a7b55a60a11d9ea345edc8"
#room_id = "65b6158b2ba06c8f8a5f8368"
#bot_token = "76b1f50e81d4a6ce4faf9cd2a8e0796507edbeb5f5702e71b530875b90d21720"


my_bot = BotDefinition(getattr(import_module(bot_file_name), bot_class_name)(), room_id2, bot_token2)

while True:
    try:
        definitions = [my_bot]
        arun(main(definitions))
    except Exception as e:
        print(f"An exception occourred: {e}")
        traceback.print_exc()
        time.sleep(1)