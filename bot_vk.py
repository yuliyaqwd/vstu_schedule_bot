import json
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from config import VK_TOKEN, VK_GROUP_ID
from core.main import main, user_states, get_user_group, save_user_group, extract_group

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, VK_GROUP_ID)


def get_main_keyboard():
    """Главное меню бота"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('По группе', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('По преподавателю', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('По аудитории', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Настройки', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def get_day_week_keyboard():
    """Клавиатура с днями недели - показывается ПОД расписанием"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Сегодня', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Завтра', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Эта неделя', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('След. неделя', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('🔙 Главное меню', color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()


def get_settings_keyboard(saved_group):
    """Клавиатура настроек"""
    keyboard = VkKeyboard(one_time=False)
    if saved_group:
        keyboard.add_button(f'Группа: {saved_group}', color=VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button('Изменить группу', color=VkKeyboardColor.PRIMARY)
    else:
        keyboard.add_button('Сохранить группу', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Назад', color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()


BUTTON_ACTIONS = {
    'По группе': 'group',
    'По преподавателю': 'teacher',
    'По аудитории': 'room',
    'Настройки': 'settings',
    'Сегодня': 'today',
    'Завтра': 'tomorrow',
    'Эта неделя': 'this_week',
    'След. неделя': 'next_week',
    '🔙 Главное меню': 'back',
    'Назад': 'back',
    'Сохранить группу': 'save_group',
    'Изменить группу': 'change_group'
}

print(" Бот запущен")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        msg = event.obj.message
        raw_text = msg.get('text', '').strip()
        user_id = msg['from_id']
        peer_id = msg['peer_id']

        payload = msg.get('payload')
        button_action = None

        if payload:
            try:
                payload_data = json.loads(payload)
                button_label = payload_data.get('label', '')
                button_action = BUTTON_ACTIONS.get(button_label)
            except:
                pass
        else:
            button_action = BUTTON_ACTIONS.get(raw_text)

        try:
            user_name = vk.users.get(user_ids=user_id)[0]['first_name']
        except:
            user_name = "Пользователь"

        response_text = ""
        keyboard = get_main_keyboard()
        is_schedule = False

        if button_action:

            if button_action == 'settings':
                saved_group = get_user_group(user_id)
                response_text = "⚙️ Настройки"
                if saved_group:
                    response_text += f"\n\nВаша группа: {saved_group}"
                else:
                    response_text += "\n\nУ вас ещё нет сохранённой группы"
                keyboard = get_settings_keyboard(saved_group)

            elif button_action in ['save_group', 'change_group']:
                user_states[user_id] = {'state': 'WAITING_GROUP'}
                msg_text = "новый номер группы" if button_action == 'change_group' else "номер вашей группы (например: ПОАС-1.1)"
                response_text = f"✏️ Введите {msg_text}"
                keyboard = get_main_keyboard()

            elif button_action == 'back':
                user_states.pop(user_id, None)
                response_text = "Главное меню"
                keyboard = get_main_keyboard()

            elif button_action == 'group':
                user_states[user_id] = {'state': 'WAITING_GROUP_FOR_SCHEDULE'}
                response_text = "✏️ Введите номер группы"
                keyboard = get_main_keyboard()

            elif button_action == 'teacher':
                user_states[user_id] = {'state': 'WAITING_TEACHER'}
                response_text = "✏️ Введите фамилию преподавателя"
                keyboard = get_main_keyboard()

            elif button_action == 'room':
                user_states[user_id] = {'state': 'WAITING_ROOM'}
                response_text = "✏️ Введите номер аудитории"
                keyboard = get_main_keyboard()

            elif button_action in ['today', 'tomorrow', 'this_week', 'next_week']:
                state_data = user_states.get(user_id, {})
                current_group = state_data.get('viewing_group')
                viewing_type = state_data.get('viewing_type', 'group')

                if not current_group:
                    current_group = get_user_group(user_id)
                    viewing_type = 'group'

                if current_group:
                    user_states[user_id] = {
                        'state': 'VIEWING_SCHEDULE',
                        'viewing_group': current_group,
                        'viewing_type': viewing_type
                    }

                    time_map = {
                        'today': 'сегодня',
                        'tomorrow': 'завтра',
                        'this_week': 'эта неделя',
                        'next_week': 'след. неделя'
                    }

                    if viewing_type == 'group':
                        query = f"расписание {current_group} {time_map[button_action]}"
                    elif viewing_type == 'teacher':
                        query = f"преподаватель {current_group} {time_map[button_action]}"
                    elif viewing_type == 'room':
                        query = f"аудитория {current_group} {time_map[button_action]}"
                    else:
                        query = f"расписание {current_group} {time_map[button_action]}"

                    response_text = main(query, user_name, user_id)
                    keyboard = get_day_week_keyboard()
                    is_schedule = True
                else:
                    user_states[user_id] = {
                        'state': 'WAITING_GROUP_FOR_TIME',
                        'time_context': button_action
                    }
                    time_labels = {
                        'today': 'сегодня',
                        'tomorrow': 'завтра',
                        'this_week': 'эту неделю',
                        'next_week': 'следующую неделю'
                    }
                    response_text = f"✏️ Введите номер группы для просмотра на {time_labels[button_action]}"
                    keyboard = get_main_keyboard()

        elif raw_text:
            if user_id in user_states:
                state_data = user_states[user_id]
                state = state_data.get('state')

                if state == 'WAITING_GROUP':
                    group = extract_group(raw_text)
                    if group:
                        save_user_group(user_id, group)
                        user_states.pop(user_id, None)
                        response_text = f"✅ Группа {group} сохранена!"
                        keyboard = get_main_keyboard()
                    else:
                        response_text = "❌ Не удалось распознать группу."
                        keyboard = get_main_keyboard()

                elif state == 'WAITING_GROUP_FOR_SCHEDULE':
                    group = raw_text
                    user_states[user_id] = {
                        'state': 'VIEWING_SCHEDULE',
                        'viewing_group': group,
                        'viewing_type': 'group'
                    }
                    response_text = main(f"расписание {group} сегодня", user_name, user_id)
                    keyboard = get_day_week_keyboard()
                    is_schedule = True

                elif state == 'WAITING_TEACHER':
                    teacher = raw_text
                    user_states[user_id] = {
                        'state': 'VIEWING_SCHEDULE',
                        'viewing_group': teacher,
                        'viewing_type': 'teacher'
                    }
                    response_text = main(f"преподаватель {teacher}", user_name, user_id)
                    keyboard = get_day_week_keyboard()
                    is_schedule = True

                elif state == 'WAITING_ROOM':
                    room = raw_text
                    user_states[user_id] = {
                        'state': 'VIEWING_SCHEDULE',
                        'viewing_group': room,
                        'viewing_type': 'room'
                    }
                    response_text = main(f"аудитория {room}", user_name, user_id)
                    keyboard = get_day_week_keyboard()
                    is_schedule = True

                elif state == 'WAITING_GROUP_FOR_TIME':
                    group = raw_text
                    time_context = state_data.get('time_context')

                    user_states[user_id] = {
                        'state': 'VIEWING_SCHEDULE',
                        'viewing_group': group,
                        'viewing_type': 'group'
                    }

                    time_map = {
                        'today': 'сегодня',
                        'tomorrow': 'завтра',
                        'this_week': 'эта неделя',
                        'next_week': 'след. неделя'
                    }

                    query = f"расписание {group} {time_map[time_context]}"
                    response_text = main(query, user_name, user_id)
                    keyboard = get_day_week_keyboard()
                    is_schedule = True

                elif state == 'VIEWING_SCHEDULE':
                    text_button_action = BUTTON_ACTIONS.get(raw_text)

                    if text_button_action in ['today', 'tomorrow', 'this_week', 'next_week']:
                        current_group = state_data.get('viewing_group')
                        viewing_type = state_data.get('viewing_type', 'group')

                        if current_group:
                            time_map = {
                                'today': 'сегодня',
                                'tomorrow': 'завтра',
                                'this_week': 'эта неделя',
                                'next_week': 'след. неделя'
                            }

                            if viewing_type == 'group':
                                query = f"расписание {current_group} {time_map[text_button_action]}"
                            elif viewing_type == 'teacher':
                                query = f"преподаватель {current_group} {time_map[text_button_action]}"
                            elif viewing_type == 'room':
                                query = f"аудитория {current_group} {time_map[text_button_action]}"
                            else:
                                query = f"расписание {current_group} {time_map[text_button_action]}"

                            response_text = main(query, user_name, user_id)
                            keyboard = get_day_week_keyboard()
                            is_schedule = True
                        else:
                            response_text = "❌ Группа не найдена"
                            keyboard = get_main_keyboard()
                            user_states.pop(user_id, None)
                    elif text_button_action == 'back':
                        user_states.pop(user_id, None)
                        response_text = "Главное меню"
                        keyboard = get_main_keyboard()
                    else:
                        response_text = main(raw_text, user_name, user_id)
                        keyboard = get_main_keyboard()
                        user_states.pop(user_id, None)

                else:
                    response_text = main(raw_text, user_name, user_id)
                    keyboard = get_main_keyboard()
            else:
                response_text = main(raw_text, user_name, user_id)
                keyboard = get_main_keyboard()

                group = extract_group(raw_text)
                if group and any(x in raw_text.lower() for x in ['сегодня', 'завтра', 'неделя', 'расписание']):
                    user_states[user_id] = {
                        'state': 'VIEWING_SCHEDULE',
                        'viewing_group': group,
                        'viewing_type': 'group'
                    }
                    keyboard = get_day_week_keyboard()
                    is_schedule = True

        if response_text and (
                '📅' in response_text or '📆' in response_text or 'Группа:' in response_text or 'Преподаватель:' in response_text or 'Аудитория:' in response_text):
            keyboard = get_day_week_keyboard()
            is_schedule = True

        if not response_text or not response_text.strip():
            response_text = "Неизвестная команда."
            keyboard = get_main_keyboard()

        try:
            vk.messages.send(
                peer_id=peer_id,
                random_id=get_random_id(),
                message=response_text,
                keyboard=keyboard
            )
        except Exception as e:
            print(f"Ошибка отправки: {e}")