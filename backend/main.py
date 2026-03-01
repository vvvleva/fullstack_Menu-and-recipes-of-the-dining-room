"""Точка входа приложения."""
import sys
import threading
import uvicorn

from app import app
from core.server import check_frontend_files, open_browser_later, print_startup_info, run_frontend_server

if __name__ == "__main__":
    frontend_ok = check_frontend_files()

    if frontend_ok:
        threading.Thread(target=run_frontend_server, daemon=True).start()
        threading.Thread(target=open_browser_later, daemon=True).start()

    print_startup_info(frontend_ok)

    try:
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\nОстановка приложения...")
        sys.exit(0)
