import json
import os
import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple

SCHEDULE_FOLDER = "schedule"
USERS_FILE = "users.json"

CLASS_TIMES = {
    1: "8:30 - 9:15", 2: "9:20 - 10:00",
    3: "10:10 - 10:55", 4: "11:00 - 11:40",
    5: "11:50 - 12:35", 6: "12:40 - 13:20",
    7: "13:40 - 14:25", 8: "14:30 - 15:10",
    9: "15:20 - 16:05", 10: "16:10 - 16:50",
    11: "17:00 - 17:45", 12: "17:50 - 18:30",
    13: "18:35 - 20:00", 14: "18:35 - 20:00",
    15: "20:05 - 21:30", 16: "20:05 - 21:30",
}

HOUR_TO_PAIR = {
    1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4,
    9: 5, 10: 5, 11: 6, 12: 6, 13: 7, 14: 7, 15: 8, 16: 8,
}

PAIR_TIMES = {
    1: "8:30 - 10:00", 2: "10:10 - 11:40", 3: "11:50 - 13:20", 4: "13:40 - 15:10",
    5: "15:20 - 16:50", 6: "17:00 - 18:30", 7: "18:35 - 20:05", 8: "20:05 - 21:30",
}

user_states = {}
_schedules_cache = None
_schedules_last_modified = None


def load_users() -> Dict[str, Any]:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_users(users: Dict[str, Any]):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_user_group(user_id: int) -> Optional[str]:
    return load_users().get(str(user_id), {}).get('group')


def save_user_group(user_id: int, group: str):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {}
    users[str(user_id)]['group'] = group
    users[str(user_id)]['updated_at'] = datetime.now().strftime("%d.%m.%Y %H:%M")
    save_users(users)


def load_schedules() -> Dict[str, Any]:
    global _schedules_cache, _schedules_last_modified

    if not os.path.exists(SCHEDULE_FOLDER):
        os.makedirs(SCHEDULE_FOLDER)
        return {}

    current_modified = {
        f: os.path.getmtime(os.path.join(SCHEDULE_FOLDER, f))
        for f in os.listdir(SCHEDULE_FOLDER) if f.endswith('.json')
    }

    if _schedules_cache is not None and current_modified == _schedules_last_modified:
        return _schedules_cache

    schedules = {}
    for filename in current_modified:
        filepath = os.path.join(SCHEDULE_FOLDER, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                schedules[filename] = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки {filename}: {e}")

    _schedules_cache = schedules
    _schedules_last_modified = current_modified
    return schedules


def get_week_type_for_date(target_date: datetime) -> str:
    week_number = target_date.isocalendar()[1]
    return "first_week" if week_number % 2 == 0 else "second_week"


def get_weekday_name(date_obj: datetime) -> str:
    weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    return weekdays[date_obj.weekday()]


def convert_hour_to_pair(hour: int) -> int:
    return HOUR_TO_PAIR.get(hour, 0)


def parse_hours(hours: List[str]) -> tuple:
    if not hours:
        return (99, 99)
    try:
        time_str = hours[0]
        if '-' in time_str:
            start = int(time_str.split('-')[0])
            start_pair = convert_hour_to_pair(start)
            return (start_pair, start_pair)
        else:
            hour = int(time_str)
            pair = convert_hour_to_pair(hour)
            return (pair, pair)
    except:
        return (99, 99)


def extract_group(text: str) -> Optional[str]:
    pattern = r'([А-Я]{2,5}-\d+\.\d+|[А-Я]{2,5}-\d+|[А-Я]-\d+)'
    match = re.search(pattern, text.upper())
    return match.group(1).replace(' ', '') if match else None


def extract_teacher(text: str) -> Optional[str]:
    keywords = ['преподаватель', 'учитель', 'препода']
    words = text.split()

    for i, word in enumerate(words):
        if word.lower() in keywords and i + 1 < len(words):
            raw = words[i + 1].split('.')[0] if '.' in words[i + 1] else words[i + 1]
            return raw.title()

    if words:
        last = words[-1].strip('.,!?;:')
        if len(last) > 2 and last[0].isupper():
            return last.split('.')[0].title() if '.' in last else last.title()
    return None


def extract_room(text: str) -> str:
    for pattern in [r'([А-ЯВ]-\d+)', r'(\d{3,4})']:
        match = re.search(pattern, text.upper())
        if match:
            return match.group(1)
    return None


def get_next_monday() -> date:
    today = date.today()
    days = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days)


def get_current_monday() -> date:
    return date.today() - timedelta(days=date.today().weekday())


def _get_pair_range_from_hours(hours_list: List[str]) -> Tuple[Optional[int], Optional[int]]:
    """
    Вычисляет диапазон пар (начало, конец) на основе списка часов из JSON.
    Пример: ["5-6", "7-8"] -> часы 5,6,7,8 -> пары 3,4 -> возвращает (3, 4)
    """
    start_pair = None
    end_pair = None

    if not hours_list:
        return (None, None)

    all_pairs = []

    for item in hours_list:
        if '-' in item:
            parts = item.split('-')
            try:
                h_start = int(parts[0])
                h_end = int(parts[1])
                p_start = convert_hour_to_pair(h_start)
                p_end = convert_hour_to_pair(h_end)
                # Добавляем все пары в диапазоне
                all_pairs.extend(range(p_start, p_end + 1))
            except ValueError:
                continue
        else:
            try:
                h = int(item)
                all_pairs.append(convert_hour_to_pair(h))
            except ValueError:
                continue

    if all_pairs:
        return (min(all_pairs), max(all_pairs))

    return (None, None)


def _format_lesson(lesson: Dict, pair_num: int) -> List[str]:
    teachers = lesson.get("participants", {}).get("teachers", [])
    subject = lesson.get("subject", "")

    # Фильтрация учителей, если имя есть в предмете
    teachers = [t for t in teachers if t.upper() not in subject.upper() and len(t) > 3]
    teacher_str = ", ".join(teachers) if teachers else "Преподаватель не указан"

    places = lesson.get("places", [])
    places = [p for p in places if not re.match(r'\d{2}\.\d{2}', p)]
    place_str = ", ".join(places) if places else "Аудитория не указана"

    groups = lesson.get("participants", {}).get("student_groups", [])
    group_str = ", ".join(groups) if groups else "Группа не указана"

    # БЕРЕМ ТИП ПРЯМО ИЗ JSON (kind)
    kind_display = lesson.get("kind", "")

    # Формируем суффикс. Если в JSON есть kind (лекция, лабораторная работа), используем его.
    if kind_display and kind_display.lower() != "без названия":
        type_suffix = f" ({kind_display})"
    else:
        type_suffix = ""

    time_str = PAIR_TIMES.get(pair_num, "Время не указано")

    return [
        f"{pair_num}. 📖 {subject}{type_suffix}",
        f"   ⏰ {time_str}",
        f"   👤 {teacher_str}",
        f"   🏫 {place_str}",
        f"   👥 {group_str}",
        ""
    ]


def _format_day(lessons: List[Dict], date_obj: datetime, show_date: bool = True) -> List[str]:
    result = []

    if show_date:
        result.append(f"\n📅 {date_obj.strftime('%d.%m.%Y')} | {get_weekday_name(date_obj)}\n")

    if not lessons:
        if show_date:
            result.append("❌ Занятий нет\n")
        return result

    for lesson in lessons:
        hours_list = lesson.get("hours", [])
        start_pair, end_pair = _get_pair_range_from_hours(hours_list)

        if start_pair is None or end_pair is None:
            continue

        # ГЛАВНОЕ ИСПРАВЛЕНИЕ:
        # Цикл проходит по КАЖДОЙ паре в диапазоне.
        # Если лаба идет с 3 по 4 пару (диапазон 3..4), цикл выполнится дважды:
        # 1. Для пары 3
        # 2. Для пары 4
        # Таким образом, длинная лаба отображается двумя пунктами.
        for pair_num in range(start_pair, end_pair + 1):
            result.extend(_format_lesson(lesson, pair_num))

    return result


def format_schedule(lessons: List[Dict], target_date: datetime, **kwargs) -> str:
    if not lessons:
        return f"📅 {target_date.strftime('%d.%m.%Y')} | {get_weekday_name(target_date)}\n\n❌ Занятий нет."

    return "\n".join(_format_day(lessons, target_date, show_date=True))


def format_week_schedule(lessons_by_day: Dict[int, List[Dict]], start_date: datetime, **kwargs) -> str:
    end_date = start_date + timedelta(days=6)
    result = [f"📆 Неделя ({start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')})\n"]

    for i in range(7):
        current_date = start_date + timedelta(days=i)
        lessons = lessons_by_day.get(current_date.weekday(), [])
        result.extend(_format_day(lessons, current_date, show_date=True))

    return "\n".join(result)


def get_schedule_for_date(target_date: datetime, group: Optional[str] = None,
                          teacher: Optional[str] = None, room: Optional[str] = None) -> List[Dict]:
    schedules = load_schedules()
    result = []
    date_str = target_date.strftime("%d.%m.%Y")
    weekday_idx = target_date.weekday()
    week_type = get_week_type_for_date(target_date)

    for schedule in schedules.values():
        for lesson in schedule.get("table", {}).get("grid", []):
            if lesson.get("week_day_index") != weekday_idx:
                continue
            if lesson.get("week") and lesson.get("week") != week_type:
                continue
            holds_on = lesson.get("holds_on_date", [])
            if holds_on and date_str not in holds_on:
                continue
            if group:
                groups = lesson.get("participants", {}).get("student_groups", [])
                if not any(group.lower() in g.lower() for g in groups):
                    continue
            if teacher:
                teachers = lesson.get("participants", {}).get("teachers", [])
                if not any(teacher.lower() in t.lower() for t in teachers):
                    continue
            if room:
                places = lesson.get("places", [])
                if not any(room in p for p in places):
                    continue
            result.append(lesson)

    result.sort(key=lambda x: _get_pair_range_from_hours(x.get("hours", []))[0] or 99)
    return result


def get_schedule_by_group(text: str, user_name: str) -> str:
    text_lower = text.lower().strip()
    group = extract_group(text)

    if not group:
        return "❌ Не получается определить группу."

    if "сегодня" in text_lower:
        target_date = datetime.now()
    elif "завтра" in text_lower:
        target_date = datetime.now() + timedelta(days=1)
    elif "эта неделя" in text_lower or "текущая неделя" in text_lower:
        start_date = get_current_monday()
        lessons_by_day = {
            d.weekday(): get_schedule_for_date(d, group=group)
            for i, d in
            enumerate(datetime.combine(start_date + timedelta(days=i), datetime.min.time()) for i in range(7))
        }
        lessons_by_day = {k: v for k, v in lessons_by_day.items() if v}
        return format_week_schedule(lessons_by_day, datetime.combine(start_date, datetime.min.time()))
    elif "следующая неделя" in text_lower or "след неделя" in text_lower or "след. неделя" in text_lower:
        start_date = get_next_monday()
        lessons_by_day = {
            d.weekday(): get_schedule_for_date(d, group=group)
            for i, d in
            enumerate(datetime.combine(start_date + timedelta(days=i), datetime.min.time()) for i in range(7))
        }
        lessons_by_day = {k: v for k, v in lessons_by_day.items() if v}
        return format_week_schedule(lessons_by_day, datetime.combine(start_date, datetime.min.time()))
    else:
        target_date = datetime.now()

    if "сегодня" in text_lower or "завтра" in text_lower or not any(x in text_lower for x in ['неделя']):
        lessons = get_schedule_for_date(target_date, group=group)
        return format_schedule(lessons, target_date)

    return format_schedule(get_schedule_for_date(target_date, group=group), target_date)


def get_schedule_by_teacher(text: str, user_name: str) -> str:
    text_lower = text.lower().strip()
    teacher = extract_teacher(text)

    if not teacher:
        return "❌ Укажите фамилию преподавателя"

    if "завтра" in text_lower:
        target_date = datetime.now() + timedelta(days=1)
    elif "эта неделя" in text_lower or "текущая неделя" in text_lower:
        start_date = get_current_monday()
        lessons_by_day = {
            d.weekday(): get_schedule_for_date(d, teacher=teacher)
            for i, d in
            enumerate(datetime.combine(start_date + timedelta(days=i), datetime.min.time()) for i in range(7))
        }
        lessons_by_day = {k: v for k, v in lessons_by_day.items() if v}
        return f"👨‍🏫 Преподаватель: {teacher}\n\n" + format_week_schedule(lessons_by_day, datetime.combine(start_date,
                                                                                                           datetime.min.time()))
    elif "следующая неделя" in text_lower or "след неделя" in text_lower or "след. неделя" in text_lower:
        start_date = get_next_monday()
        lessons_by_day = {
            d.weekday(): get_schedule_for_date(d, teacher=teacher)
            for i, d in
            enumerate(datetime.combine(start_date + timedelta(days=i), datetime.min.time()) for i in range(7))
        }
        lessons_by_day = {k: v for k, v in lessons_by_day.items() if v}
        return f"👨‍🏫 Преподаватель: {teacher}\n\n" + format_week_schedule(lessons_by_day, datetime.combine(start_date,
                                                                                                           datetime.min.time()))
    else:
        target_date = datetime.now()

    lessons = get_schedule_for_date(target_date, teacher=teacher)
    if not lessons:
        return f"👨‍🏫 {target_date.strftime('%d.%m.%y')} | {get_weekday_name(target_date)}\n\nЗанятий у преподавателя {teacher} нет"

    result = f"👨‍🏫 {target_date.strftime('%d.%m.%y')} | {get_weekday_name(target_date)}\n\n"
    for lesson in lessons:
        hours_list = lesson.get("hours", [])
        start_pair, end_pair = _get_pair_range_from_hours(hours_list)

        if start_pair is None or end_pair is None:
            continue

        for pair_num in range(start_pair, end_pair + 1):
            time_str = PAIR_TIMES.get(pair_num, "Время не указано")
            subject = lesson.get("subject", "Без названия")
            groups = lesson.get("participants", {}).get("student_groups", [])
            group_str = ", ".join(groups) if groups else "Группа не указана"
            places = ", ".join(lesson.get("places", ["?"]))
            result += f"⏰ {time_str}\n📖 {subject}\n👥 {group_str}\n📍 {places}\n\n"

    return result


def get_schedule_by_room(text: str, user_name: str) -> str:
    text_lower = text.lower().strip()
    room = extract_room(text)

    if not room:
        return "❌ Укажите номер аудитории"

    if "завтра" in text_lower:
        target_date = datetime.now() + timedelta(days=1)
    elif "эта неделя" in text_lower or "текущая неделя" in text_lower:
        start_date = get_current_monday()
        lessons_by_day = {
            d.weekday(): get_schedule_for_date(d, room=room)
            for i, d in
            enumerate(datetime.combine(start_date + timedelta(days=i), datetime.min.time()) for i in range(7))
        }
        lessons_by_day = {k: v for k, v in lessons_by_day.items() if v}
        return f"📍 Аудитория: {room}\n\n" + format_week_schedule(lessons_by_day,
                                                                 datetime.combine(start_date, datetime.min.time()))
    elif "следующая неделя" in text_lower or "след неделя" in text_lower or "след. неделя" in text_lower:
        start_date = get_next_monday()
        lessons_by_day = {
            d.weekday(): get_schedule_for_date(d, room=room)
            for i, d in
            enumerate(datetime.combine(start_date + timedelta(days=i), datetime.min.time()) for i in range(7))
        }
        lessons_by_day = {k: v for k, v in lessons_by_day.items() if v}
        return f"📍 Аудитория: {room}\n\n" + format_week_schedule(lessons_by_day,
                                                                 datetime.combine(start_date, datetime.min.time()))
    else:
        target_date = datetime.now()

    lessons = get_schedule_for_date(target_date, room=room)
    if not lessons:
        return f"📍 {target_date.strftime('%d.%m.%y')} | {get_weekday_name(target_date)}\n\nВ аудитории {room} занятий нет"

    result = f"📍 {target_date.strftime('%d.%m.%y')} | {get_weekday_name(target_date)}\n\n"
    for lesson in lessons:
        hours_list = lesson.get("hours", [])
        start_pair, end_pair = _get_pair_range_from_hours(hours_list)

        if start_pair is None or end_pair is None:
            continue

        for pair_num in range(start_pair, end_pair + 1):
            time_str = PAIR_TIMES.get(pair_num, "Время не указано")
            subject = lesson.get("subject", "Без названия")
            teachers = ", ".join(lesson.get("participants", {}).get("teachers", ["?"]))
            groups = lesson.get("participants", {}).get("student_groups", [])
            group_str = ", ".join(groups) if groups else "Группа не указана"
            result += f"⏰ {time_str}\n📖 {subject}\n👨‍🏫 {teachers}\n👥 {group_str}\n\n"

    return result


def main(text: str, user_name: str = "пользователь", user_id: int = None) -> str:
    text_lower = text.lower().strip()

    if text_lower in ['привет', 'здравствуй', 'hello', 'hi', '/start', 'start']:
        saved_group = get_user_group(user_id) if user_id else None
        group_info = f"\n\n📌 Ваша сохранённая группа: {saved_group}" if saved_group else ""
        return f"👋 Привет, {user_name}!{group_info}\n\nВыбери кнопку, чтобы увидеть расписание"

    if any(x in text_lower for x in ['преподаватель', 'учитель']):
        return get_schedule_by_teacher(text, user_name)

    if any(x in text_lower for x in ['аудитория', 'кабинет', 'ауд']):
        return get_schedule_by_room(text, user_name)

    group = extract_group(text)
    if not group and user_id:
        group = get_user_group(user_id)

    if group or any(x in text_lower for x in ['сегодня', 'завтра', 'неделя', 'расписание']):
        if not group:
            return "📚 Напиши номер группы"
        return get_schedule_by_group(text, user_name)

    return "Неизвестная команда. Используй кнопки"
