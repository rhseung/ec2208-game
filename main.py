def main() -> int:
    try:
        from renderer.tui import DungeonApp
    except ModuleNotFoundError as error:
        if error.name not in {"algorithms", "components", "game", "renderer"}:
            print(f"Missing dependency: {error.name}")
            print("Run this project with: python3 run.py")
            return 1
        raise

    DungeonApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
