import os
import sys
import time


# ============================================================
#                    НАСТРОЙКИ
# ============================================================

CONSOLE_NAME = "GAME STATION"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
#                    ИГРЫ
# ============================================================

GAMES = {

    "1": {
        "name": "Among Us",
        "file": "Among Us.url"
    },

    "2": {
        "name": "Dizzy Two",
        "file": "Dizzy Two (Диззи 2).lnk"
    },

    "3": {
        "name": "Counter-Strike 2",
        "file": "Counter-Strike 2.url"
    },

    "4": {
        "name": "The Backrooms",
        "file": "The Backrooms Game FREE Edition.lnk"
    }
}


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
    print("                   PC GAME LAUNCHER")
    print()
    print("=" * 70)
    print()


# ============================================================
#                    ПУТЬ К ИГРЕ
# ============================================================

def get_game_path(game):

    return os.path.join(
        BASE_DIR,
        game["file"]
    )


# ============================================================
#                    ПРОВЕРКА ИГРЫ
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
            f"  [{number}] 🎮 {game['name']:<30} {status}"
        )

    print("-" * 70)

    print()
    print("  [R] 🔄 Обновить список")
    print("  [I] ℹ️  Информация")
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

    print("Проверка ярлыка...")
    print()

    # --------------------------------------------------------
    # ЯРЛЫК НЕ НАЙДЕН
    # --------------------------------------------------------

    if not os.path.isfile(game_path):

        print("❌ ОШИБКА")
        print()

        print("Ярлык игры не найден:")

        print()
        print(game_path)

        print()

        print("Убедись, что файл находится")
        print("в той же папке, что и launch.py.")

        pause()

        return

    # --------------------------------------------------------
    # ЯРЛЫК НАЙДЕН
    # --------------------------------------------------------

    print("✅ Ярлык найден!")
    print()

    print("Файл:")

    print(game["file"])

    print()

    print("🚀 Запуск игры...")
    print()

    try:

        # Windows открывает .lnk и .url
        os.startfile(game_path)

        print("=" * 70)
        print()
        print("             ✅ ИГРА УСПЕШНО ЗАПУЩЕНА!")
        print()
        print(f"                  {game['name']}")
        print()
        print("=" * 70)

        time.sleep(2)

        input(
            "\nНажми Enter, чтобы вернуться в меню..."
        )

    except Exception as error:

        print()
        print("❌ НЕ УДАЛОСЬ ОТКРЫТЬ ИГРУ")
        print()

        print("Ошибка:")
        print(error)

        print()

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

    print("Этот лаунчер открывает ярлыки")
    print("игр формата .lnk и .url.")
    print()

    print("Файлы должны находиться")
    print("в той же папке, что и launch.py.")
    print()

    print("Поддерживаются:")

    print()
    print("  • .lnk — ярлык Windows")
    print("  • .url — интернет/Steam ярлык")

    print()

    print("Текущая папка:")

    print()
    print(BASE_DIR)

    print()
    print("-" * 70)

    pause()


# ============================================================
#                    АНИМАЦИЯ
# ============================================================

def startup_animation():

    clear_screen()

    print()
    print("=" * 70)
    print()
    print("                    🎮 GAME STATION")
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
            print("                    GAME STATION")
            print()
            print("                Спасибо за игру! 🎮")
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

            launch_game(
                GAMES[choice]
            )

        # ----------------------------------------------------
        # ОШИБКА
        # ----------------------------------------------------

        else:

            print()
            print("❌ Неверный выбор!")

            time.sleep(1)


# ============================================================
#                    ЗАПУСК
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        clear_screen()

        print()
        print("=" * 70)
        print()
        print("              Программа закрыта.")
        print()
        print("=" * 70)
        print()

        sys.exit()
