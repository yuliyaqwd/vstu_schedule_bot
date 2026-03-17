import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from config import VK_TOKEN, VK_GROUP_ID
from core.main import main

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, VK_GROUP_ID)

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        msg = event.obj.message
        text = msg['text']
        user_id = msg['from_id']
        peer_id = msg['peer_id']

        try:
            user_name = vk.users.get(user_ids=user_id)[0]['first_name']
        except:
            user_name = "пользователь"

        vk.messages.send(
            peer_id=peer_id,
            random_id=get_random_id(),
            message=main(text, user_name)
        )