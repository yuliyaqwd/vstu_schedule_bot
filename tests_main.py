import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
from datetime import datetime, timedelta, date
import sys
import os.path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import (
    extract_group, extract_teacher, extract_room,
    get_week_type_for_date, get_weekday_name,
    get_pair_number, get_class_time, get_lab_time_range,
    get_lesson_type, parse_hours,
    get_schedule_for_date, format_schedule, format_week_schedule,
    get_schedule_by_group, get_schedule_by_teacher, get_schedule_by_room,
    main, get_user_group, save_user_group, load_users, save_users,
    PAIR_TIMES, CLASS_TIMES, HOUR_TO_PAIR
)


class TestExtractFunctions(unittest.TestCase):

    def test_extract_group(self):
        self.assertEqual(extract_group("ПОАС-1.1"), "ПОАС-1.1")
        self.assertEqual(extract_group("расписание ПОАС-1.1 сегодня"), "ПОАС-1.1")
        self.assertEqual(extract_group("ПРИН-367"), "ПРИН-367")
        self.assertEqual(extract_group("А-101"), "А-101")
        self.assertEqual(extract_group("нет группы"), None)

    def test_extract_teacher(self):
        self.assertEqual(extract_teacher("преподаватель Иванов"), "Иванов")
        self.assertEqual(extract_teacher("учитель Петров"), "Петров")
        self.assertEqual(extract_teacher("препода Сидоров"), "Сидоров")
        self.assertEqual(extract_teacher("Иванов"), "Иванов")
        self.assertEqual(extract_teacher("нет"), None)

    def test_extract_room(self):
        self.assertEqual(extract_room("аудитория В-902"), "В-902")
        self.assertEqual(extract_room("кабинет 101"), "101")
        self.assertEqual(extract_room("ауд 234"), "234")
        self.assertEqual(extract_room("нет"), None)


class TestDateFunctions(unittest.TestCase):

    def test_get_weekday_name(self):
        test_date = datetime(2024, 1, 1)
        self.assertEqual(get_weekday_name(test_date), "понедельник")

        test_date = datetime(2024, 1, 2)
        self.assertEqual(get_weekday_name(test_date), "вторник")

    def test_get_week_type_for_date(self):
        test_date = datetime(2024, 1, 1)
        result = get_week_type_for_date(test_date)
        self.assertIn(result, ["first_week", "second_week"])


class TestTimeFunctions(unittest.TestCase):

    def test_get_pair_number(self):
        self.assertEqual(get_pair_number(["3"]), 3)
        self.assertEqual(get_pair_number(["3-6"]), 3)
        self.assertEqual(get_pair_number([]), 0)

    def test_get_class_time(self):
        self.assertEqual(get_class_time(["3"]), "11:50 - 13:20")
        self.assertEqual(get_class_time(["3-4"]), "11:50 - 13:20, 13:40 - 15:10")
        self.assertEqual(get_class_time([]), "Время не указано")

    def test_get_lab_time_range(self):
        start, end = get_lab_time_range(["3-4"])
        self.assertEqual(start, "11:50")
        self.assertEqual(end, "15:10")

        start, end = get_lab_time_range(["3"])
        self.assertEqual(start, "11:50")
        self.assertEqual(end, "13:20")

    def test_get_lesson_type(self):
        self.assertEqual(get_lesson_type(["ГРУППА1", "ГРУППА2"], ["1"]), "лекция")
        self.assertEqual(get_lesson_type(["ГРУППА1"], ["1-2"]), "лабораторная работа")
        self.assertEqual(get_lesson_type(["ГРУППА1"], ["1"]), "практика")
        self.assertEqual(get_lesson_type([], ["1"]), "")

    def test_parse_hours(self):
        self.assertEqual(parse_hours(["3-6"]), (3, 3))
        self.assertEqual(parse_hours(["5"]), (5, 5))
        self.assertEqual(parse_hours([]), (99, 99))


class TestScheduleFunctions(unittest.TestCase):

    @patch('core.main.load_schedules')
    def test_get_schedule_for_date_group(self, mock_load):
        mock_schedule = {
            "schedule1.json": {
                "table": {
                    "grid": [
                        {
                            "week_day_index": 0,
                            "week": "first_week",
                            "hours": ["1"],
                            "participants": {"student_groups": ["ПОАС-1.1"]},
                            "subject": "Тест",
                            "places": ["101"]
                        }
                    ]
                }
            }
        }
        mock_load.return_value = mock_schedule

        test_date = datetime(2024, 1, 1)
        result = get_schedule_for_date(test_date, group="ПОАС-1.1")
        self.assertEqual(len(result), 0)

    @patch('core.main.load_schedules')
    def test_get_schedule_for_date_teacher(self, mock_load):
        mock_schedule = {
            "schedule1.json": {
                "table": {
                    "grid": [
                        {
                            "week_day_index": 0,
                            "week": "first_week",
                            "hours": ["1"],
                            "participants": {"teachers": ["Иванов"]},
                            "subject": "Тест",
                            "places": ["101"]
                        }
                    ]
                }
            }
        }
        mock_load.return_value = mock_schedule

        test_date = datetime(2024, 1, 1)
        result = get_schedule_for_date(test_date, teacher="Иванов")
        self.assertEqual(len(result), 0)

    @patch('core.main.load_schedules')
    def test_get_schedule_for_date_empty(self, mock_load):
        mock_load.return_value = {}

        test_date = datetime(2024, 1, 1)
        result = get_schedule_for_date(test_date, group="НЕТ")
        self.assertEqual(len(result), 0)

    def test_format_schedule_empty(self):
        result = format_schedule([], datetime(2024, 1, 1))
        self.assertIn("Занятий нет", result)

    def test_format_schedule_with_lessons(self):
        lessons = [
            {
                "hours": ["1"],
                "subject": "Тест",
                "participants": {"teachers": ["Иванов"], "student_groups": ["ПОАС-1.1"]},
                "places": ["101"],
                "kind": ""
            }
        ]
        result = format_schedule(lessons, datetime(2024, 1, 1))
        self.assertIn("Тест", result)
        self.assertIn("Иванов", result)


class TestScheduleByGroup(unittest.TestCase):

    @patch('core.main.get_schedule_for_date')
    def test_get_schedule_by_group_today(self, mock_get):
        mock_get.return_value = []
        result = get_schedule_by_group("расписание ПОАС-1.1 сегодня", "Тест")
        self.assertIsInstance(result, str)

    @patch('core.main.get_schedule_for_date')
    def test_get_schedule_by_group_no_group(self, mock_get):
        result = get_schedule_by_group("расписание", "Тест")
        self.assertEqual(result, "❌ Не получается определить группу.")


class TestScheduleByTeacher(unittest.TestCase):

    @patch('core.main.get_schedule_for_date')
    def test_get_schedule_by_teacher_no_teacher(self, mock_get):
        result = get_schedule_by_teacher("преподаватель", "Тест")
        self.assertEqual(result, "❌ Укажите фамилию преподавателя")

    @patch('core.main.get_schedule_for_date')
    def test_get_schedule_by_teacher_with_teacher(self, mock_get):
        mock_get.return_value = []
        result = get_schedule_by_teacher("преподаватель Иванов", "Тест")
        self.assertIsInstance(result, str)


class TestScheduleByRoom(unittest.TestCase):

    @patch('core.main.get_schedule_for_date')
    def test_get_schedule_by_room_no_room(self, mock_get):
        result = get_schedule_by_room("аудитория", "Тест")
        self.assertEqual(result, "❌ Укажите номер аудитории")

    @patch('core.main.get_schedule_for_date')
    def test_get_schedule_by_room_with_room(self, mock_get):
        mock_get.return_value = []
        result = get_schedule_by_room("аудитория 101", "Тест")
        self.assertIsInstance(result, str)


class TestMainFunction(unittest.TestCase):

    @patch('core.main.get_user_group')
    def test_main_hello(self, mock_group):
        mock_group.return_value = None
        result = main("привет", "Тест", 123)
        self.assertIn("Привет", result)

    @patch('core.main.get_user_group')
    def test_main_hello_with_group(self, mock_group):
        mock_group.return_value = "ПОАС-1.1"
        result = main("привет", "Тест", 123)
        self.assertIn("ПОАС-1.1", result)

    @patch('core.main.get_schedule_by_teacher')
    def test_main_teacher(self, mock_teacher):
        mock_teacher.return_value = "Расписание преподавателя"
        result = main("преподаватель Иванов", "Тест")
        self.assertEqual(result, "Расписание преподавателя")

    @patch('core.main.get_schedule_by_room')
    def test_main_room(self, mock_room):
        mock_room.return_value = "Расписание аудитории"
        result = main("аудитория 101", "Тест")
        self.assertEqual(result, "Расписание аудитории")

    @patch('core.main.extract_group')
    @patch('core.main.get_user_group')
    @patch('core.main.get_schedule_by_group')
    def test_main_group(self, mock_schedule, mock_group, mock_extract):
        mock_extract.return_value = "ПОАС-1.1"
        mock_group.return_value = None
        mock_schedule.return_value = "Расписание группы"

        result = main("расписание ПОАС-1.1 сегодня", "Тест", 123)
        self.assertEqual(result, "Расписание группы")

    def test_main_unknown(self):
        result = main("что-то непонятное", "Тест")
        self.assertEqual(result, "Неизвестная команда. Используй кнопки")


class TestUserFunctions(unittest.TestCase):

    @patch('core.main.load_users')
    def test_get_user_group(self, mock_load):
        mock_load.return_value = {"123": {"group": "ПОАС-1.1"}}
        result = get_user_group(123)
        self.assertEqual(result, "ПОАС-1.1")

    @patch('core.main.load_users')
    def test_get_user_group_not_found(self, mock_load):
        mock_load.return_value = {}
        result = get_user_group(123)
        self.assertEqual(result, None)

    @patch('core.main.load_users')
    @patch('core.main.save_users')
    def test_save_user_group(self, mock_save, mock_load):
        mock_load.return_value = {}
        save_user_group(123, "ПОАС-1.1")
        mock_save.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='{}')
    @patch('os.path.exists')
    def test_load_users_file_exists(self, mock_exists, mock_file):
        mock_exists.return_value = True
        result = load_users()
        self.assertEqual(result, {})

    @patch('os.path.exists')
    def test_load_users_file_not_exists(self, mock_exists):
        mock_exists.return_value = False
        result = load_users()
        self.assertEqual(result, {})


class TestWeekSchedule(unittest.TestCase):

    @patch('core.main.get_schedule_for_date')
    def test_format_week_schedule(self, mock_get):
        mock_get.return_value = []

        start_date = datetime(2024, 1, 1)
        lessons_by_day = {i: [] for i in range(7)}

        result = format_week_schedule(lessons_by_day, start_date)
        self.assertIn("Неделя", result)

    @patch('core.main.get_schedule_for_date')
    def test_get_schedule_by_group_this_week(self, mock_get):
        mock_get.return_value = []

        result = get_schedule_by_group("ПОАС-1.1 эта неделя", "Тест")
        self.assertIsInstance(result, str)

    @patch('core.main.get_schedule_for_date')
    def test_get_schedule_by_group_next_week(self, mock_get):
        mock_get.return_value = []

        result = get_schedule_by_group("ПОАС-1.1 следующая неделя", "Тест")
        self.assertIsInstance(result, str)


class TestLabSchedule(unittest.TestCase):

    def test_format_lab_with_range(self):
        lesson = {
            "hours": ["3-6"],
            "subject": "ТЕСТИРОВАНИЕ ПО",
            "participants": {
                "teachers": ["Шашков Д.А.", "Морозов Д.А."],
                "student_groups": ["ПРИН-367"]
            },
            "places": ["В-902"],
            "kind": ""
        }

        lessons = [lesson]
        result = format_schedule(lessons, datetime(2024, 1, 1))

        self.assertIn("3 и 4 и 5 и 6", result)
        self.assertIn("11:50 - 13:20, 13:40 - 15:10, 15:20 - 16:50, 17:00 - 18:30", result)
        self.assertIn("ТЕСТИРОВАНИЕ ПО", result)

    def test_format_lab_with_two_pairs(self):
        lesson = {
            "hours": ["3-4"],
            "subject": "ТЕСТИРОВАНИЕ ПО",
            "participants": {
                "teachers": ["Шашков Д.А."],
                "student_groups": ["ПРИН-367"]
            },
            "places": ["В-902"],
            "kind": ""
        }

        lessons = [lesson]
        result = format_schedule(lessons, datetime(2024, 1, 1))

        self.assertIn("3 и 4", result)
        self.assertIn("11:50 - 13:20, 13:40 - 15:10", result)

    def test_format_regular_lesson(self):
        lesson = {
            "hours": ["1"],
            "subject": "Математика",
            "participants": {
                "teachers": ["Иванов И.И."],
                "student_groups": ["ПОАС-1.1"]
            },
            "places": ["101"],
            "kind": ""
        }

        lessons = [lesson]
        result = format_schedule(lessons, datetime(2024, 1, 1))

        self.assertIn("1.", result)
        self.assertIn("Математика", result)
        self.assertIn("8:30 - 10:00", result)


if __name__ == '__main__':
    unittest.main()