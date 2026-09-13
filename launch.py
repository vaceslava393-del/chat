import os
import subprocess
import sys
import time


# ============================================================
#                    НАСТРОЙКИ КОНСОЛИ
# ============================================================

CONSOLE_NAME = "GAME STATION"

GAMES = {
    "1": {
        "name": "Pacman",
        "folder": "Pacman",
        "exe": "Pacman.exe"
    },

    "2": {
        "name": "Among Us",
        "folder": "AmongUs",
        "exe": "AmongUs.exe"
    },

    "3": {
        "name": "Roblox",
        "folder": "Roblox",
        "exe": "Roblox.exe"
    },

    "4": {
        "name": "Terraria",
        "folder": "Terraria",
        "exe": "Terraria.exe"
    },

    "5": {
        "name": "Street Racing 3D",
        "folder": "StreetRacing",
        "exe": "StreetRacing.exe"
    },

    "6": {
        "name": "The Dizzy",
        "folder": "TheDizzy",
        "exe": "TheDizzy.exe"
    }
}


# ============================================================
#                    ПУТЬ К ПРОЕКТУ
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GAMES_DIR = os.path.join(BASE_DIR, "games")


# ============================================================
#                    ОЧИСТКА ЭКРАНА
# ============================================================

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


# ============================================================
#                    ПАУЗА
# ============================================================

def pause():
    input("\nНажми Enter для продолжения...")


# ============================================================
#                    ЗАГОЛОВОК
# ============================================================

def show_header():

    print("=" * 70)
    print()
    print("                    🎮 GAME STATION")
    print()
    print("              PC GAME LAUNCHER")
    print()
    print("=" * 70)
    print()


# ============================================================
#                    ПРОВЕРКА ИГРЫ
# ============================================================

def get_game_path(game):

    folder = game["folder"]
    exe = game["exe"]

    game_folder = os.path.join(GAMES_DIR, folder)

    game_exe = os.path.join(game_folder, exe)

    return game_exe


# ============================================================
#                    СТАТУС ИГРЫ
# ============================================================

def game_status(game):

    path = get_game_path(game)

    if os.path.isfile(path):
        return "✅ ГОТОВА"

    return "❌ НЕ НАЙДЕНА"


# ============================================================
#                    ПОКАЗ ИГР
# ============================================================

def show_games():

    print("                         ИГРЫ")
    print("-" * 70)

    for number, game in GAMES.items():

        status = game_status(game)

        print(
            f"  [{number}] 🎮 {game['name']:<25} {status}"
        )

    print("-" * 70)

    print()
    print("  [R] 🔄 Обновить список")
    print("  [0] 🚪 Выход")
    print()


# ============================================================
#                    ЗАПУСК ИГРЫ
# ============================================================

def launch_game(game):

    clear_screen()

    show_header()

    print(f"🎮 Игра: {game['name']}")
    print()

    game_path = get_game_path(game)

    print("Проверка файла...")
    print()

    if not os.path.isfile(game_path):

        print("❌ ОШИБКА")
        print()
        print("Файл игры не найден.")
        print()
        print("Программа ищет:")
        print(game_path)
        print()

        print("Создай папку:")

        print(
            os.path.join(
                GAMES_DIR,
                game["folder"]
            )
        )

        print()

        print("И положи туда файл:")

        print(game["exe"])

        pause()

        return

    print("Файл найден!")
    print()
    print("🚀 Запуск игры...")
    print()

    try:

        # Запуск EXE
        subprocess.Popen(
            [game_path],
            cwd=os.path.dirname(game_path)
        )

        print("=" * 70)
        print()
        print("             ✅ ИГРА УСПЕШНО ЗАПУЩЕНА!")
        print()
        print(f"             {game['name']}")
        print()
        print("=" * 70)

        time.sleep(2)

        input("\nНажми Enter, чтобы вернуться в меню...")

    except Exception as error:

        print()
        print("❌ НЕ УДАЛОСЬ ЗАПУСТИТЬ ИГРУ")
        print()
        print("Ошибка:")
        print(error)

        pause()


# ============================================================
#                    ИНФОРМАЦИЯ
# ============================================================

def show_info():

    clear_screen()

    show_header()

    print("                         INFO")
    print("-" * 70)
    print()
    print("🎮 GAME STATION")
    print()
    print("Это консольный лаунчер для запуска")
    print("игр с помощью .exe файлов.")
    print()
    print("Игры должны находиться внутри папки:")
    print()
    print("games/")
    print()
    print("Каждая игра должна иметь свою папку.")
    print()
    print("-" * 70)

    pause()


# ============================================================
#                    АНИМАЦИЯ ЗАПУСКА
# ============================================================

def startup_animation():

    clear_screen()

    print()
    print("=" * 70)
    print()
    print("                    GAME STATION")
    print()
    print("=" * 70)
    print()

    print("Запуск консоли", end="", flush=True)

    for _ in range(5):

        time.sleep(0.3)

        print(".", end="", flush=True)

    print()

    time.sleep(0.5)


# ============================================================
#                    ГЛАВНОЕ МЕНЮ
# ============================================================

def main():

    startup_animation()

    while True:

        clear_screen()

        show_header()

        show_games()

        choice = input("Выбери игру: ").strip().lower()

        # ----------------------------------------------------
        # ВЫХОД
        # ----------------------------------------------------

        if choice == "0":

            clear_screen()

            print()
            print("=" * 70)
            print()
            print("                  GAME STATION")
            print()
            print("              Спасибо за игру! 🎮")
            print()
            print("=" * 70)
            print()

            time.sleep(2)

            sys.exit()

        # ----------------------------------------------------
        # ОБНОВИТЬ
        # ----------------------------------------------------

        elif choice == "r":

            clear_screen()

            print()
            print("🔄 Обновление списка игр...")

            time.sleep(1)

        # ----------------------------------------------------
        # ИНФОРМАЦИЯ
        # ----------------------------------------------------

        elif choice == "i":

            show_info()

        # ----------------------------------------------------
        # ИГРА
        # ----------------------------------------------------

        elif choice in GAMES:

            launch_game(GAMES[choice])

        # ----------------------------------------------------
        # ОШИБКА
        # ----------------------------------------------------

        else:

            print()
            print("❌ Неверный выбор!")

            time.sleep(1)


# ============================================================
#                    ЗАПУСК ПРОГРАММЫ
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        clear_screen()

        print()
        print("Программа закрыта.")

        sys.exit()