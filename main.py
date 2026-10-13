"""
Entry point dell'applicazione.
Avvia il gestore della UI (PyQt6).
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

import config

# Importa l'interfaccia utente dal modulo dedicato
from ui import CalcolatoreFeriePAR

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if config.ICON_PATH:
        app.setWindowIcon(QIcon(config.ICON_PATH))
    window = CalcolatoreFeriePAR()
    window.show()
    sys.exit(app.exec())
