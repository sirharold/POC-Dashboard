"""
EPMAPS Dashboard - Main Application Entry Point

This file now uses the refactored class-based architecture.
The original monolithic code has been moved to app_monolithic_backup.py

Usage:
    streamlit run app.py
"""

from dashboard_manager import DashboardManager


def main():
    """Main application entry point."""
    dashboard = DashboardManager()
    dashboard.run()


if __name__ == "__main__":
    main()