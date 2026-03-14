"""
Entry point dell'applicazione.
Avvia il gestore della UI (PyQt6).
"""

import sys
from PyQt6.QtWidgets import QApplication

# Importa l'interfaccia utente dal modulo dedicato
from ui import CalcolatoreFeriePAR

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalcolatoreFeriePAR()
    window.show()
    sys.exit(app.exec())