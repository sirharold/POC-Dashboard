"""
EPMAPS Dashboard - Refactored with Classes

This is the refactored version of the Dashboard EPMAPS application.
The code has been reorganized into classes for better maintainability,
but the UI behavior and appearance remain exactly the same.

Usage:
    streamlit run app_refactored.py
"""

from dashboard_manager import DashboardManager


def main():
    """Main application entry point."""
    dashboard = DashboardManager()
    dashboard.run()


if __name__ == "__main__":
    main()