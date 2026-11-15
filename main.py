"""
Entry point dell'applicazione.
Avvia il gestore della UI (PyQt6).
"""

import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

import config

# Importa l'interfaccia utente dal modulo dedicato
from ui import CalcolatoreFeriePAR

def main() -> None:
    """Entry point dell'applicazione (usato anche dallo script gui_scripts di setup.py)."""
    app = QApplication(sys.argv)
    try:
        if config.ICON_PATH:
            app.setWindowIcon(QIcon(config.ICON_PATH))
        window = CalcolatoreFeriePAR()
        window.show()
        sys.exit(app.exec())
    except Exception:
        # In un build --noconsole l'eccezione uscirebbe senza traccia: la logghiamo
        # su file e la mostriamo in un dialogo, cosi' il crash non resta silenzioso.
        config.logger.critical("Crash all'avvio:\n" + traceback.format_exc())
        QMessageBox.critical(
            None, "Errore imprevisto",
            "L'applicazione si e' arrestata per un errore imprevisto.\n"
            f"Dettagli nel log: {config.FILE_LOG}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
