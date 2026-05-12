import argparse
import sys


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MpvTube launcher")
    parser.add_argument("--gui", action="store_true", help="Run graphical interface")
    parser.add_argument("--min", action="store_true", help="Run minimal line-based terminal mode")
    args = parser.parse_args()

    if args.gui:
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as e:
            print(f"GUI unavailable: {e}", file=sys.stderr)
            sys.exit(1)

        from app.gui import MainWindow

        app = QApplication(sys.argv)
        w = MainWindow()
        w.show()
        sys.exit(app.exec())
    else:
        from app.tui import run_tui, run_tui_min
        run_tui_min() if args.min else run_tui()
