"""
Dialoghi secondari della UI, separati dalla finestra principale (ui.py)
per isolarne il ciclo di vita e semplificarne il testing.
"""

from typing import Callable

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox


class CalendarioCollettivoDialog(QDialog):
    """Dialogo "Imposta Giorni Collettivi": permette di incollare il testo della mail
    aziendale e di farlo analizzare per estrarre le date di chiusura collettiva."""

    def __init__(self, parent, testo_iniziale: str, on_analizza: Callable[[str], int]):
        """
        Args:
            parent: finestra proprietaria del dialogo.
            testo_iniziale: testo mail già salvato in precedenza (se presente).
            on_analizza: callback invocata con il testo incollato dall'utente;
                deve analizzarlo, salvarlo, e restituire il numero di date trovate.
        """
        super().__init__(parent)
        self._on_analizza = on_analizza

        self.setWindowTitle("Imposta Giorni Collettivi")
        self.resize(650, 450)
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel("Incolla qui le righe estratte dalla mail ufficiale aziendale.\n"))

        self.txt_edit = QTextEdit()
        self.txt_edit.setPlainText(testo_iniziale)
        lay.addWidget(self.txt_edit)

        btn_salva = QPushButton("Analizza e Salva Date")
        btn_salva.clicked.connect(self._on_salva)
        lay.addWidget(btn_salva)

    def _on_salva(self) -> None:
        testo = self.txt_edit.toPlainText()
        date_trovate = self._on_analizza(testo)
        QMessageBox.information(
            self, "Analisi Completata",
            f"Aggiunte {date_trovate} date valide al Calendario Collettivo.\n"
            "Le date del calendario vengono scalate automaticamente dai saldi come giornate intere da 8h."
        )
        self.accept()
