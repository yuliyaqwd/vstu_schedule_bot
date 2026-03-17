def main(text: str, user_name: str = "пользователь") -> str:
    text_lower = text.lower().strip()

    if text_lower in ['привет', 'здравствуй', 'hello', 'hi', '/start', 'start']:
        return f"Привет, {user_name}!"

    return f"{text}"