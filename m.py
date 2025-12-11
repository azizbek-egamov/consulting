class Uz:
    hello_text = "Salom, hush kelibsiz!"
    class err:
        error_text = "Xatolik yuz berdi."
        logout_text = "Tizimdan chiqdingiz."

class Ru:
    hello_text = "Здравствуйте, добро пожаловать!"
    class err:
        error_text = "Произошла ошибка."
        logout_text = "Вы вышли из системы."

class Language:
    def __new__(cls, code: str):
        if code == "uz":
            return Uz
        elif code == "ru":
            return Ru
        else:
            raise ValueError("Bunday til yo'q")
lang = Language("ru")
    

print(lang.err.error_text)
