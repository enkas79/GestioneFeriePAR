"""
Layer di Presentazione (UI).
Costruisce la finestra grafica utilizzando le classi di PyQt6.
"""

import os
import html
from datetime import date
from typing import Any, Dict, List, Tuple

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QDateEdit, QDoubleSpinBox,
                             QCheckBox, QPushButton, QGroupBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QComboBox, QMessageBox,
                             QAbstractItemView, QLineEdit, QFileDialog, QInputDialog,
                             QGridLayout, QDialog, QTextBrowser,
                             QDialogButtonBox, QProgressBar, QTextEdit)
from PyQt6.QtCore import Qt, QDate, QUrl
from PyQt6.QtGui import QFont, QColor, QAction, QTextDocument, QKeySequence, QShortcut, QDesktopServices
from PyQt6.QtPrintSupport import QPrinter

import config
import utils
from models import DataManager, BustaPageParser, CalcolatoreLogica, HAS_PYPDF, UpdateManager


class CalcolatoreFeriePAR(QMainWindow):
    """Finestra principale dell'applicazione (Gestione UI e interazione utente)."""

    def __init__(self) -> None:
        super().__init__()

        # Il titolo viene ora generato automaticamente tramite config.py
        self.setWindowTitle(f"Gestione Ferie/PAR - Pro v{config.APP_VERSION}")

        self.resize(1100, 750)

        self.dm = DataManager()
        self.parser = BustaPageParser()
        self.calc = CalcolatoreLogica()

        mesi_nomi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                     "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        self.mese_busta = mesi_nomi[date.today().month - 1]
        self.anno_busta = date.today().year

        self._ultimo_calc_ferie: Dict[str, float] = {}
        self._ultimo_calc_par: Dict[str, float] = {}

        self._applica_stile()
        self.crea_menu_bar()

        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)

        self.crea_sezione_anagrafica()
        self.crea_sezione_inserimento()
        self.crea_sezione_risultati()
        self.crea_sezione_comandi()

        self._registra_shortcuts()

        self.dm.carica()
        self._popola_ui_da_dm()
        self.calcola()

    def _applica_stile(self) -> None:
        self.setStyleSheet("""
            QMainWindow { background-color: #f4f4f4; }
            QGroupBox { font-weight: bold; border: 1px solid #aaa; border-radius: 6px;
                        margin-top: 12px; padding: 15px; background-color: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #333; }
            QLabel { font-size: 13px; color: #333; }
            QLineEdit, QDateEdit, QDoubleSpinBox, QComboBox, QTextEdit {
                padding: 6px; border: 1px solid #ccc; border-radius: 4px;
                font-size: 13px; min-height: 20px; }
            QPushButton { background-color: #0078d7; color: white; border-radius: 4px;
                          padding: 8px 15px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #005a9e; }
            QPushButton#btn_rimuovi  { background-color: #d9534f; }
            QPushButton#btn_esci     { background-color: #6c757d; }
            QPushButton#btn_stampa   { background-color: #6610f2; }
            QPushButton#btn_csv      { background-color: #17a2b8; }
            QPushButton#btn_edit_res { background-color: #f0ad4e; color: white;
                                       border: none; font-size: 11px; padding: 4px; }
            QPushButton#btn_calendario { background-color: #28a745; }
            QPushButton#btn_calendario:hover { background-color: #218838; }
            QTableWidget {
                gridline-color: #e3e7ee;
                font-size: 13px;
                alternate-background-color: #f8fafc;
                selection-background-color: #cfe8ff;
                selection-color: #1f2937;
                border: 1px solid #d7dde6;
                border-radius: 6px;
            }
            QTableWidget::item { padding: 6px; }
            QTableWidget#tab_saldi {
                font-size: 12px;
                background-color: #ffffff;
                alternate-background-color: #f6f8fb;
            }
            QTableWidget#tab_saldi::item { padding: 8px 6px; }
            QHeaderView::section {
                background-color: #eef2f7;
                padding: 6px;
                border: 1px solid #d0d7e2;
                font-weight: bold;
                color: #263445;
            }
            QMenuBar { background-color: #e0e0e0; font-size: 14px; }
            QMenuBar::item:selected { background-color: #ccc; }
            QProgressBar { border: 1px solid #999; border-radius: 4px; text-align: center;
                           height: 20px; background-color: #e9ecef; }
        """)

    def _registra_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.azione_salva_manuale)
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.stampa_report)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.rimuovi_assenza)

    def crea_menu_bar(self) -> None:
        mb = self.menuBar()
        file_menu = mb.addMenu("File")

        a_salva_db = QAction("Salva database come...", self)
        a_salva_db.triggered.connect(self.salva_database_come)
        a_carica_db = QAction("Carica database...", self)
        a_carica_db.triggered.connect(self.carica_database_da_file)
        a_nuovo_db = QAction("Nuovo database / Azzera dati", self)
        a_nuovo_db.triggered.connect(self.reset_dati)

        file_menu.addAction(a_salva_db)
        file_menu.addAction(a_carica_db)
        file_menu.addAction(a_nuovo_db)
        file_menu.addSeparator()

        a_pdf = QAction("Esporta PDF completo  (Ctrl+P)", self)
        a_pdf.triggered.connect(self.stampa_report)
        a_csv = QAction("Esporta storico CSV", self)
        a_csv.triggered.connect(self.esporta_csv)

        file_menu.addAction(a_pdf)
        file_menu.addAction(a_csv)
        file_menu.addSeparator()

        a_esci = QAction("Esci", self)
        a_esci.triggered.connect(self.close)
        file_menu.addAction(a_esci)

        help_menu = mb.addMenu("Aiuto")

        a_guida = QAction("Guida Utente", self)
        a_guida.triggered.connect(self.mostra_guida)

        a_update = QAction("Controlla Aggiornamenti", self)
        a_update.triggered.connect(self.controlla_aggiornamenti)

        a_info = QAction("Info", self)
        a_info.triggered.connect(self.mostra_info)

        help_menu.addAction(a_guida)
        help_menu.addAction(a_update)
        help_menu.addSeparator()
        help_menu.addAction(a_info)

    def controlla_aggiornamenti(self) -> None:
        """Controlla se esiste una versione più recente su GitHub."""
        has_update, latest_ver, url = UpdateManager.check_for_updates()

        if has_update:
            risposta = QMessageBox.question(
                self, "Aggiornamento Disponibile",
                f"È disponibile una nuova versione: <b>{latest_ver}</b><br>"
                f"Versione attuale: {config.APP_VERSION}<br><br>"
                "Vuoi aprire la pagina di download?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if risposta == QMessageBox.StandardButton.Yes:
                # Apre l'URL predefinito nel browser del sistema
                QDesktopServices.openUrl(QUrl(url))
        else:
            QMessageBox.information(
                self, "Aggiornamenti",
                f"Stai già utilizzando la versione più recente ({config.APP_VERSION}).\n"
                "Nessun aggiornamento trovato."
            )

    def reset_dati(self) -> None:
        risposta = QMessageBox.warning(
            self, "Reset Generale Dati",
            "Sei sicuro di voler cancellare TUTTI i dati inseriti?\n\n"
            "Questa operazione eliminerà definitivamente il file di salvataggio.\n"
            "Azione NON reversibile.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta == QMessageBox.StandardButton.Yes:
            self.dm.elimina_salvataggi()
            self.dm.reset()
            self._popola_ui_da_dm()
            self.calcola()
            QMessageBox.information(self, "Reset", "Dati azzerati con successo.")

    def _nome_database_default(self) -> str:
        """Genera un nome file leggibile per il salvataggio del database."""
        nome = (self.txt_nominativo.text().strip() or self.dm.nominativo or "dipendente").strip()
        anno = str(date.today().year)
        anni = {item["data"].year() for item in self._assenze_effettive_e_programmate()} if hasattr(self, "tab_storico") else set()
        if len(anni) == 1:
            anno = str(next(iter(anni)))
        nome_pulito = "".join(ch if ch.isalnum() else "_" for ch in nome).strip("_") or "dipendente"
        return f"FeriePAR_{nome_pulito}_{anno}.json"

    def salva_database_come(self) -> None:
        """Esporta tutto il database corrente in un file JSON scelto dall'utente."""
        self.salva_dati_su_file()
        nome_default = self._nome_database_default()
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva database", nome_default, "Database JSON (*.json);;Tutti i file (*)"
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        success, err = self.dm.salva_su_file(path)
        if success:
            QMessageBox.information(self, "Database salvato", f"Database salvato correttamente:\n{path}")
        else:
            QMessageBox.critical(self, "Errore salvataggio database", f"Impossibile salvare il database:\n{err}")

    def carica_database_da_file(self) -> None:
        """Carica un database JSON salvato e lo rende il database corrente."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Carica database", "", "Database JSON (*.json);;Tutti i file (*)"
        )
        if not path:
            return

        risposta = QMessageBox.question(
            self,
            "Carica database",
            "Il database selezionato sostituirà tutti i dati attualmente caricati.\n\n"
            "Prima di procedere, salva il database corrente se vuoi conservarlo.\n\n"
            "Vuoi continuare?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return

        success, err = self.dm.carica_da_file(path)
        if not success:
            QMessageBox.critical(self, "Errore caricamento database", f"Impossibile caricare il database:\n{err}")
            return

        self._popola_ui_da_dm()
        self.calcola()
        self.salva_dati_su_file()
        QMessageBox.information(self, "Database caricato", f"Database caricato correttamente:\n{path}")

    def crea_sezione_anagrafica(self) -> None:
        group = QGroupBox("1. Anagrafica Dipendente")
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setContentsMargins(10, 15, 10, 10)

        self.txt_matricola = QLineEdit()
        self.txt_matricola.setPlaceholderText("Matr.")
        self.txt_matricola.setFixedWidth(80)
        self.txt_matricola.textChanged.connect(self.salva_dati_su_file)

        self.txt_nominativo = QLineEdit()
        self.txt_nominativo.setPlaceholderText("Inserisci Nome e Cognome")
        self.txt_nominativo.setFixedWidth(200)
        self.txt_nominativo.textChanged.connect(self.salva_dati_su_file)

        self.date_assunzione = QDateEdit()
        self.date_assunzione.setDisplayFormat(config.DATE_FORMAT_DISPLAY)
        self.date_assunzione.setCalendarPopup(True)
        self.date_assunzione.setFixedWidth(110)
        self.date_assunzione.dateChanged.connect(self.cancella_cache_e_ricalcola)

        self.check_patrono = QCheckBox("S.Patrono (+8h)")
        self.check_patrono.stateChanged.connect(self.cancella_cache_e_ricalcola)

        btn_calendario = QPushButton("Calendario Ferie")
        btn_calendario.setObjectName("btn_calendario")
        btn_calendario.setFixedWidth(140)
        btn_calendario.setToolTip("Incolla l'estratto della mail aziendale.")
        btn_calendario.clicked.connect(self.apri_dialog_calendario)

        btn_import = QPushButton("Carica Buste Paga")
        btn_import.setFixedWidth(140)
        btn_import.clicked.connect(self.importa_busta_paga)

        grid.addWidget(QLabel("Dipendente:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.txt_nominativo, 0, 1, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(QLabel("Matricola:"), 0, 2, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.txt_matricola, 0, 3, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(QLabel("Data Assunz.:"), 0, 4, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.date_assunzione, 0, 5, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self.check_patrono, 0, 6, Qt.AlignmentFlag.AlignLeft)

        h_btn_layout = QHBoxLayout()
        h_btn_layout.addStretch()
        h_btn_layout.addWidget(btn_calendario)
        h_btn_layout.addWidget(btn_import)
        grid.addLayout(h_btn_layout, 0, 8)
        grid.setColumnStretch(7, 1)

        group.setLayout(grid)
        self.main_layout.addWidget(group)

    def apri_dialog_calendario(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Imposta Giorni Collettivi")
        dlg.resize(650, 450)
        lay = QVBoxLayout(dlg)

        lbl_info = QLabel("Incolla qui le righe estratte dalla mail ufficiale aziendale.\n")
        lay.addWidget(lbl_info)

        txt_edit = QTextEdit()
        txt_edit.setPlainText(self.dm.calendario.testo_mail)
        lay.addWidget(txt_edit)

        btn_salva = QPushButton("Analizza e Salva Date")

        def on_salva() -> None:
            testo = txt_edit.toPlainText()
            date_trovate = self.dm.calendario.aggiorna_da_testo(testo)
            QMessageBox.information(
                dlg, "Analisi Completata",
                f"Aggiunte {date_trovate} date valide al Calendario Collettivo.\n"
                "Le date del calendario vengono scalate automaticamente dai saldi come giornate intere da 8h."
            )
            self.salva_dati_su_file()
            self.aggiorna_tabella_storico()
            self.calcola()
            dlg.accept()

        btn_salva.clicked.connect(on_salva)
        lay.addWidget(btn_salva)
        dlg.exec()

    def crea_sezione_inserimento(self) -> None:
        group = QGroupBox("2. Registra Nuova Assenza (Manuale)")
        grid = QGridLayout()
        grid.setSpacing(15)

        self.date_inizio = QDateEdit()
        self.date_inizio.setDisplayFormat(config.DATE_FORMAT_DISPLAY)
        self.date_inizio.setCalendarPopup(True)
        self.date_inizio.setDate(QDate.currentDate())
        self.date_inizio.setMinimumWidth(120)

        self.check_periodo = QCheckBox("Abilita Periodo")
        self.check_periodo.stateChanged.connect(self.toggle_periodo)

        self.date_fine = QDateEdit()
        self.date_fine.setDisplayFormat(config.DATE_FORMAT_DISPLAY)
        self.date_fine.setCalendarPopup(True)
        self.date_fine.setDate(QDate.currentDate())
        self.date_fine.setEnabled(False)
        self.date_fine.setMinimumWidth(120)

        grid.addWidget(QLabel("Dal:"), 0, 0)
        grid.addWidget(self.date_inizio, 0, 1)
        grid.addWidget(self.check_periodo, 0, 2)
        grid.addWidget(QLabel("Al:"), 0, 3)
        grid.addWidget(self.date_fine, 0, 4)
        grid.setColumnStretch(5, 1)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems([config.TIPO_FERIE, config.TIPO_PAR])
        self.combo_tipo.setMinimumWidth(120)

        self.check_giorno_intero = QCheckBox("Giornata Intera (8h)")
        self.check_giorno_intero.setChecked(True)
        self.check_giorno_intero.stateChanged.connect(self.toggle_giorno_intero)

        self.spin_ore = QDoubleSpinBox()
        self.spin_ore.setRange(0.1, 8.0)
        self.spin_ore.setDecimals(2)
        self.spin_ore.setValue(8.0)
        self.spin_ore.setSuffix(" ore")
        self.spin_ore.setEnabled(False)
        self.spin_ore.setFixedWidth(100)

        btn_add = QPushButton("Inserisci")
        btn_add.setFixedWidth(140)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self.aggiungi_assenza)

        grid.addWidget(QLabel("Tipo:"), 1, 0)
        grid.addWidget(self.combo_tipo, 1, 1)
        grid.addWidget(self.check_giorno_intero, 1, 2)
        grid.addWidget(QLabel("Ore da inserire (HH,MM es. 3,30 = 3h30m):"), 1, 3)
        grid.addWidget(self.spin_ore, 1, 4)
        grid.addWidget(btn_add, 1, 5, Qt.AlignmentFlag.AlignRight)

        group.setLayout(grid)
        self.main_layout.addWidget(group)

    def crea_sezione_risultati(self) -> None:
        h_layout = QHBoxLayout()

        group_storico = QGroupBox("Storico Utilizzi")
        vbox_storico = QVBoxLayout()

        hbox_filtro = QHBoxLayout()
        hbox_filtro.addWidget(QLabel("Filtra anno:"))
        self.combo_filtro_anno = QComboBox()
        self.combo_filtro_anno.addItem("Tutti")
        self.combo_filtro_anno.currentTextChanged.connect(self.aggiorna_tabella_storico)
        hbox_filtro.addWidget(self.combo_filtro_anno)
        hbox_filtro.addStretch()
        vbox_storico.addLayout(hbox_filtro)

        self.tab_storico = QTableWidget()
        self.tab_storico.setColumnCount(3)
        self.tab_storico.setHorizontalHeaderLabels(["Data", "Tipo", "Ore inserite"])
        self.tab_storico.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tab_storico.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tab_storico.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tab_storico.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_storico.setAlternatingRowColors(True)

        hbox_btn = QHBoxLayout()
        btn_rimuovi = QPushButton("Rimuovi Selezionati  (Del)")
        btn_rimuovi.setObjectName("btn_rimuovi")
        btn_rimuovi.clicked.connect(self.rimuovi_assenza)

        btn_csv = QPushButton("Esporta CSV")
        btn_csv.setObjectName("btn_csv")
        btn_csv.setFixedWidth(120)
        btn_csv.clicked.connect(self.esporta_csv)

        hbox_btn.addWidget(btn_rimuovi)
        hbox_btn.addWidget(btn_csv)

        vbox_storico.addWidget(self.tab_storico)
        vbox_storico.addLayout(hbox_btn)
        group_storico.setLayout(vbox_storico)

        group_saldi = QGroupBox("Saldi e ore disponibili")
        vbox_saldi = QVBoxLayout()

        hbox_hdr = QHBoxLayout()
        lbl_fifo = QLabel("Calcolo automatico su mesi chiusi. Valori finali in ore decimali: 3,5 h = 3 ore e mezza.")
        lbl_fifo.setStyleSheet("color: #666; font-style: italic;")
        btn_edit = QPushButton("Modifica Manuale Res.AP")
        btn_edit.setObjectName("btn_edit_res")
        btn_edit.setFixedWidth(165)
        btn_edit.clicked.connect(self.modifica_manuale_residui)
        hbox_hdr.addWidget(lbl_fifo)
        hbox_hdr.addStretch()
        hbox_hdr.addWidget(btn_edit)
        vbox_saldi.addLayout(hbox_hdr)

        self.tab_saldi = QTableWidget()
        self.tab_saldi.setObjectName("tab_saldi")
        self.tab_saldi.setColumnCount(9)
        self.tab_saldi.setHorizontalHeaderLabels([
            "Tipo", "Diritto\nannuo", "Residuo AP\niniziale", "AP usato\nanno prec.",
            "Maturato\nad oggi", "Usato\ntotale", "Residuo AP\nrimasto",
            "Disponibili\noggi", "Presunto\nfine anno"
        ])
        self.tab_saldi.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tab_saldi.horizontalHeader().setStretchLastSection(True)
        self.tab_saldi.horizontalHeader().setMinimumSectionSize(78)
        self.tab_saldi.verticalHeader().setVisible(False)
        self.tab_saldi.verticalHeader().setDefaultSectionSize(42)
        self.tab_saldi.setMinimumHeight(150)
        self.tab_saldi.setAlternatingRowColors(True)
        self.tab_saldi.setShowGrid(False)
        self.tab_saldi.setWordWrap(True)
        self.tab_saldi.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tab_saldi.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tab_saldi.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_saldi.setRowCount(2)
        self._imposta_cella_saldi(0, 0, config.TIPO_FERIE, evidenza="tipo")
        self._imposta_cella_saldi(1, 0, config.TIPO_PAR, evidenza="tipo")
        vbox_saldi.addWidget(self.tab_saldi)
        vbox_saldi.addSpacing(10)

        lbl_f = QLabel("Ferie disponibili oggi:")
        lbl_f.setStyleSheet("font-weight: bold;")
        self.bar_ferie = QProgressBar()
        self.bar_ferie.setTextVisible(True)
        self.bar_ferie.setFormat("0 h disponibili")

        lbl_p = QLabel("PAR disponibili oggi:")
        lbl_p.setStyleSheet("font-weight: bold;")
        self.bar_par = QProgressBar()
        self.bar_par.setTextVisible(True)
        self.bar_par.setFormat("0 h disponibili")

        vbox_saldi.addWidget(lbl_f)
        vbox_saldi.addWidget(self.bar_ferie)
        vbox_saldi.addWidget(lbl_p)
        vbox_saldi.addWidget(self.bar_par)

        self.lbl_avviso = QLabel("")
        vbox_saldi.addWidget(self.lbl_avviso)
        group_saldi.setLayout(vbox_saldi)

        h_layout.addWidget(group_storico, 30)
        h_layout.addWidget(group_saldi, 70)
        self.main_layout.addLayout(h_layout)

    def crea_sezione_comandi(self) -> None:
        hbox = QHBoxLayout()
        hbox.addStretch()

        btn_stampa = QPushButton("Esporta in PDF  (Ctrl+P)")
        btn_stampa.setObjectName("btn_stampa")
        btn_stampa.clicked.connect(self.stampa_report)
        btn_stampa.setFixedWidth(190)

        btn_salva = QPushButton("Salva Dati  (Ctrl+S)")
        btn_salva.clicked.connect(self.azione_salva_manuale)
        btn_salva.setFixedWidth(165)

        btn_esci = QPushButton("Esci")
        btn_esci.setObjectName("btn_esci")
        btn_esci.clicked.connect(self.close)
        btn_esci.setFixedWidth(100)

        hbox.addWidget(btn_stampa)
        hbox.addSpacing(10)
        hbox.addWidget(btn_salva)
        hbox.addWidget(btn_esci)

        self.main_layout.addSpacing(10)
        self.main_layout.addLayout(hbox)

    def _popola_ui_da_dm(self) -> None:
        for w in (self.txt_nominativo, self.txt_matricola,
                  self.date_assunzione, self.check_patrono):
            w.blockSignals(True)

        self.txt_nominativo.setText(self.dm.nominativo)
        self.txt_matricola.setText(self.dm.matricola)
        d = QDate.fromString(self.dm.data_assunzione, config.DATE_FORMAT_INTERNAL)
        if d.isValid():
            self.date_assunzione.setDate(d)
        self.check_patrono.setChecked(self.dm.includi_patrono)

        for w in (self.txt_nominativo, self.txt_matricola,
                  self.date_assunzione, self.check_patrono):
            w.blockSignals(False)

        self._aggiorna_combo_anni()
        self.aggiorna_tabella_storico()

    def _aggiorna_combo_anni(self) -> None:
        anni = sorted(
            {item["data"].year() for item in self.dm.storico_assenze}
            | {item["data"].year() for item in self.dm.calendario.assenze_collettive_programmate()},
            reverse=True
        )
        self.combo_filtro_anno.blockSignals(True)
        self.combo_filtro_anno.clear()
        self.combo_filtro_anno.addItem("Tutti")
        for a in anni:
            self.combo_filtro_anno.addItem(str(a))
        self.combo_filtro_anno.blockSignals(False)

    def _assenze_effettive_e_programmate(self) -> List[Dict[str, Any]]:
        """Unisce storico reale e calendario collettivo, evitando doppi conteggi."""
        righe: List[Dict[str, Any]] = [
            {**item, "origine": "Storico"} for item in self.dm.storico_assenze
        ]
        date_storico = {
            item["data"].toString(config.DATE_FORMAT_INTERNAL)
            for item in self.dm.storico_assenze
        }

        for item in self.dm.calendario.assenze_collettive_programmate():
            key = item["data"].toString(config.DATE_FORMAT_INTERNAL)
            # Se la data esiste gia' nello storico non viene duplicata: la riga reale
            # resta l'unica fonte di ore, ma viene comunque evidenziata come calendario.
            if key not in date_storico:
                righe.append(item)

        righe.sort(key=lambda x: (x["data"], x["tipo"], x.get("origine", "")))
        return righe

    def aggiorna_tabella_storico(self) -> None:
        filtro = self.combo_filtro_anno.currentText()
        self.tab_storico.setRowCount(0)

        for item in self._assenze_effettive_e_programmate():
            if filtro != "Tutti" and str(item["data"].year()) != filtro:
                continue

            row = self.tab_storico.rowCount()
            self.tab_storico.insertRow(row)

            origine = item.get("origine", "Storico")
            is_cal = self.dm.calendario.is_collettivo(item["data"])
            if origine == "Calendario":
                tipo_display = f"{item['tipo']} (Calendario)"
            elif is_cal:
                tipo_display = f"{item['tipo']} (Cal)"
            else:
                tipo_display = item["tipo"]

            it_data = QTableWidgetItem(item["data"].toString(config.DATE_FORMAT_DISPLAY))
            it_tipo = QTableWidgetItem(tipo_display)
            it_ore = QTableWidgetItem(utils.format_ore_decimali(float(item["ore"])))

            if is_cal or origine == "Calendario":
                color = QColor("#e8f4fd") if origine != "Calendario" else QColor("#fff3cd")
                it_data.setBackground(color)
                it_tipo.setBackground(color)
                it_ore.setBackground(color)
                it_tipo.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                it_tipo.setForeground(QColor("#005a9e") if origine != "Calendario" else QColor("#856404"))

            self.tab_storico.setItem(row, 0, it_data)
            self.tab_storico.setItem(row, 1, it_tipo)
            self.tab_storico.setItem(row, 2, it_ore)

    def _verifica_limite_ore(self, data_target: QDate, ore_nuove: float) -> Tuple[bool, float]:
        ore_p = sum(a["ore"] for a in self.dm.storico_assenze if a["data"] == data_target)
        return (ore_p + ore_nuove <= config.MAX_ORE_GIORNALIERE + 0.001), ore_p

    def aggiungi_assenza(self) -> None:
        tipo = self.combo_tipo.currentText()
        ore_input = self.spin_ore.value()
        ore = utils.hhmm_to_decimal(ore_input)

        if self.check_periodo.isChecked():
            start, end = self.date_inizio.date(), self.date_fine.date()
            if start > end:
                QMessageBox.warning(self, "Errore", "La data di fine deve essere successiva.")
                return
            curr, inseriti = start, 0
            while curr <= end:
                if not utils.is_giorno_festivo(curr):
                    ok, _ = self._verifica_limite_ore(curr, ore)
                    if ok:
                        self.dm.storico_assenze.append({"data": curr, "tipo": tipo, "ore": ore})
                        inseriti += 1
                curr = curr.addDays(1)
            QMessageBox.information(self, "Info", f"Inseriti {inseriti} giorni lavorativi.")
        else:
            data = self.date_inizio.date()
            ok, _ = self._verifica_limite_ore(data, ore)
            if not ok:
                QMessageBox.critical(self, "Errore", f"Superamento limite giornaliero ({config.MAX_ORE_GIORNALIERE}h).")
                return
            self.dm.storico_assenze.append({"data": data, "tipo": tipo, "ore": ore})

        self.dm.storico_assenze.sort(key=lambda x: x["data"])
        self._aggiorna_combo_anni()
        self.aggiorna_tabella_storico()
        self.salva_dati_su_file()
        self.calcola()

    def rimuovi_assenza(self) -> None:
        selected = sorted(
            {idx.row() for idx in self.tab_storico.selectedIndexes()}, reverse=True
        )
        if not selected:
            return
        reply = QMessageBox.question(
            self, "Conferma", "Cancellare le righe selezionate?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for row in selected:
                i_data = self.tab_storico.item(row, 0)
                i_tipo = self.tab_storico.item(row, 1)
                if i_data and i_tipo:
                    if "(Calendario)" in i_tipo.text():
                        # Le righe generate dal calendario non si cancellano dallo storico:
                        # per rimuoverle bisogna modificare il testo del calendario collettivo.
                        continue
                    d = QDate.fromString(i_data.text(), config.DATE_FORMAT_DISPLAY)
                    t = i_tipo.text().replace(" (Cal)", "").replace(" (Calendario)", "")
                    for i, a in enumerate(self.dm.storico_assenze):
                        if a["data"] == d and a["tipo"] == t:
                            del self.dm.storico_assenze[i]
                            break
            self._aggiorna_combo_anni()
            self.aggiorna_tabella_storico()
            self.salva_dati_su_file()
            self.calcola()

    def calcola(self) -> None:
        qd = self.date_assunzione.date()
        d_ass = date(qd.year(), qd.month(), qd.day())
        today = date.today()

        sp_ferie, sp_par = self.calc.calcola_spettanze(d_ass, self.check_patrono.isChecked())
        mesi = self.calc.calcola_mesi_maturati(d_ass, today)

        god_f_cal, god_p_cal = 0.0, 0.0
        god_f_totale, god_p_totale = 0.0, 0.0
        god_f_anno_precedente, god_p_anno_precedente = 0.0, 0.0
        anno_precedente = today.year - 1

        for x in self._assenze_effettive_e_programmate():
            anno_assenza = x["data"].year()

            # Le assenze dell'anno precedente scaricano il Residuo AP inserito/importato.
            # Questo serve per i calendari che includono ferie/PAR di fine anno precedente
            # non ancora assorbite nel valore di Residuo AP disponibile.
            if anno_assenza == anno_precedente:
                if x["tipo"] == config.TIPO_FERIE:
                    god_f_anno_precedente += x["ore"]
                elif x["tipo"] == config.TIPO_PAR:
                    god_p_anno_precedente += x["ore"]
                continue

            # Il calcolo del maturato/usato dell'anno corrente resta limitato all'anno corrente.
            if anno_assenza != today.year:
                continue

            is_cal = self.dm.calendario.is_collettivo(x["data"]) or x.get("origine") == "Calendario"
            if x["tipo"] == config.TIPO_FERIE:
                god_f_totale += x["ore"]
                if is_cal: god_f_cal += x["ore"]
            elif x["tipo"] == config.TIPO_PAR:
                god_p_totale += x["ore"]
                if is_cal: god_p_cal += x["ore"]

        mat_f = (sp_ferie / 12.0) * mesi
        mat_p = (sp_par / 12.0) * mesi

        god_f_normale = max(0.0, god_f_totale - god_f_cal)
        god_p_normale = max(0.0, god_p_totale - god_p_cal)

        res_ap_ferie_corretto = self.dm.res_ap_ferie - god_f_anno_precedente
        res_ap_par_corretto = self.dm.res_ap_par - god_p_anno_precedente

        self._ultimo_calc_ferie = self.calc.fifo_avanzato(
            sp_ferie, res_ap_ferie_corretto, mat_f, god_f_normale, god_f_cal,
            ap_scalato_anno_precedente=god_f_anno_precedente,
            res_ap_iniziale=self.dm.res_ap_ferie
        )
        self._ultimo_calc_par = self.calc.fifo_avanzato(
            sp_par, res_ap_par_corretto, mat_p, god_p_normale, god_p_cal,
            ap_scalato_anno_precedente=god_p_anno_precedente,
            res_ap_iniziale=self.dm.res_ap_par
        )

        self._aggiorna_riga(0, self._ultimo_calc_ferie, self.bar_ferie, config.TIPO_FERIE)
        self._aggiorna_riga(1, self._ultimo_calc_par, self.bar_par, config.TIPO_PAR)

    def _imposta_cella_saldi(self, row: int, col: int, testo: str,
                            evidenza: str = "normale") -> QTableWidgetItem:
        """Crea una cella dei saldi con allineamento, colori e tooltip coerenti."""
        item = QTableWidgetItem(testo)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setToolTip(testo)

        if evidenza == "tipo":
            item.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            item.setForeground(QColor("#1f2937"))
            item.setBackground(QColor("#edf2f7"))
        elif evidenza == "saldo_ok":
            item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            item.setForeground(QColor("#1f7a3a"))
            item.setBackground(QColor("#e8f7ee"))
        elif evidenza == "saldo_ko":
            item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            item.setForeground(QColor("#b42318"))
            item.setBackground(QColor("#fdecec"))
        elif evidenza == "presunto":
            item.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            item.setForeground(QColor("#344054"))
            item.setBackground(QColor("#f5f7fa"))
        elif evidenza == "attenzione":
            item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            item.setForeground(QColor("#b54708"))
            item.setBackground(QColor("#fff3cd"))

        self.tab_saldi.setItem(row, col, item)
        return item

    def _aggiorna_riga(self, row: int, r: Dict[str, float], bar: QProgressBar, tipo: str) -> None:
        """Aggiorna la riga dei saldi usando ore decimali leggibili per l'utente."""
        self._imposta_cella_saldi(row, 1, utils.format_ore_decimali(r["diritto"]))
        self._imposta_cella_saldi(row, 2, utils.format_ore_decimali(r.get("res_ap_iniziale", r["res_ap"])))
        self._imposta_cella_saldi(row, 3, utils.format_ore_decimali(r.get("ap_scalato_anno_precedente", 0.0)),
                                  evidenza="attenzione" if r.get("ap_scalato_anno_precedente", 0.0) > 0 else "normale")
        self._imposta_cella_saldi(row, 4, utils.format_ore_decimali(r["maturato"]))
        self._imposta_cella_saldi(row, 5, utils.format_ore_decimali(r["goduto_tot"]))

        if r["res_ap_netto"] == 0 and r["res_ap"] > 0:
            evidenza_ap = "attenzione"
        elif r["res_ap_netto"] < 0:
            evidenza_ap = "saldo_ko"
        else:
            evidenza_ap = "normale"
        self._imposta_cella_saldi(row, 6, utils.format_ore_decimali(r["res_ap_netto"]), evidenza=evidenza_ap)

        evidenza_saldo = "saldo_ko" if r["saldo"] < 0 else "saldo_ok"
        self._imposta_cella_saldi(row, 7, utils.format_ore_decimali(r["saldo"]), evidenza=evidenza_saldo)

        self._imposta_cella_saldi(row, 8, utils.format_ore_decimali(r.get("presunto_fine_anno", 0.0)),
                                  evidenza="presunto")
        self.tab_saldi.resizeColumnsToContents()

        totale = max(r["res_ap"] + r["diritto"], 1.0)
        saldo = max(r["saldo"], 0.0)
        percentuale = min(max(saldo / totale, 0.0), 1.0)

        if r["saldo"] < 0:
            style = "QProgressBar::chunk { background-color: #d9534f; }"
        elif percentuale < 0.25:
            style = "QProgressBar::chunk { background-color: #f0ad4e; }"
        else:
            style = "QProgressBar::chunk { background-color: #5cb85c; }"

        bar.setRange(0, 1000)
        bar.setValue(int(percentuale * 1000))
        bar.setFormat(f"{utils.format_ore_decimali(r['saldo'])} disponibili")
        bar.setStyleSheet(style)

        if r["saldo"] < 0:
            self.lbl_avviso.setText(
                f"⚠️ Attenzione: saldo {tipo} negativo ({utils.format_ore_decimali(r['saldo'])})!"
            )
            self.lbl_avviso.setStyleSheet("color: #d9534f; font-weight: bold;")
        else:
            if self._ultimo_calc_ferie.get("saldo", 0) >= 0 and self._ultimo_calc_par.get("saldo", 0) >= 0:
                self.lbl_avviso.setText("")

    def importa_busta_paga(self) -> None:
        if not HAS_PYPDF:
            QMessageBox.critical(self, "Errore", "Libreria 'pypdf' mancante.\nInstalla con: pip install pypdf")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(self, "Seleziona PDF", "", "PDF Files (*.pdf);;Text Files (*.txt)")
        if not file_paths:
            return

        ass_agg_totali = 0
        file_processati = 0

        for file_path in file_paths:
            try:
                testo = self.parser.leggi_testo(file_path)
                dati = self.parser.parse(testo)

                if dati.get("ferie"):
                    self.dm.res_ap_ferie = dati["ferie"]["res_ap"]
                if dati.get("par"):
                    self.dm.res_ap_par = dati["par"]["res_ap"]

                if dati.get("mese") and dati.get("anno"):
                    self.mese_busta = dati["mese_str"]
                    self.anno_busta = dati["anno"]
                    for g in dati["giornate"]:
                        dup = any(a["data"] == g["data"] and a["tipo"] == g["tipo"] for a in self.dm.storico_assenze)
                        if not dup:
                            self.dm.storico_assenze.append(g)
                            ass_agg_totali += 1

                file_processati += 1
            except Exception as e:
                QMessageBox.critical(self, "Errore File", f"Errore su {os.path.basename(file_path)}: {e}")

        if file_processati > 0:
            self.dm.storico_assenze.sort(key=lambda x: x["data"])
            self._aggiorna_combo_anni()
            self.aggiorna_tabella_storico()
            self.salva_dati_su_file()
            self.calcola()
            QMessageBox.information(self, "Importazione",
                                    f"Elaborati {file_processati} file. {ass_agg_totali} nuove assenze.")

    def modifica_manuale_residui(self) -> None:
        val_f, ok1 = QInputDialog.getDouble(
            self, "Modifica Ferie Res.AP", "Residuo Anno Prec. Ferie (HH,MM):",
            utils.decimal_to_hhmm(self.dm.res_ap_ferie), -1000, 3000, 2
        )
        if ok1:
            self.dm.res_ap_ferie = utils.hhmm_to_decimal(val_f)

        val_p, ok2 = QInputDialog.getDouble(
            self, "Modifica PAR Res.AP", "Residuo Anno Prec. PAR (HH,MM):",
            utils.decimal_to_hhmm(self.dm.res_ap_par), -1000, 3000, 2
        )
        if ok2:
            self.dm.res_ap_par = utils.hhmm_to_decimal(val_p)

        if ok1 or ok2:
            self.cancella_cache_e_ricalcola()

    def toggle_periodo(self) -> None:
        self.date_fine.setEnabled(self.check_periodo.isChecked())

    def toggle_giorno_intero(self) -> None:
        checked = self.check_giorno_intero.isChecked()
        if checked:
            self.spin_ore.setValue(8.0)
        self.spin_ore.setEnabled(not checked)

    def azione_salva_manuale(self) -> None:
        self.salva_dati_su_file()
        QMessageBox.information(self, "Salvataggio", "Dati salvati correttamente.")

    def cancella_cache_e_ricalcola(self) -> None:
        self.salva_dati_su_file()
        self.calcola()

    def salva_dati_su_file(self) -> None:
        success, err = self.dm.salva(
            nominativo=self.txt_nominativo.text(),
            matricola=self.txt_matricola.text(),
            data_assunzione_str=self.date_assunzione.date().toString(config.DATE_FORMAT_INTERNAL),
            includi_patrono=self.check_patrono.isChecked()
        )
        if not success:
            QMessageBox.critical(self, "Errore salvataggio", f"Impossibile salvare:\n{err}")

    def esporta_csv(self) -> None:
        nome = f"Storico_{self.dm.nominativo or 'dipendente'}.csv".replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(self, "Salva CSV", nome, "CSV (*.csv)")
        if path and self.dm.esporta_csv(path):
            QMessageBox.information(self, "Esportazione CSV", f"File salvato:\n{path}")
        elif path:
            QMessageBox.critical(self, "Errore", "Impossibile salvare il CSV.")

    def stampa_report(self) -> None:
        if not self.txt_nominativo.text().strip():
            QMessageBox.warning(self, "Dati mancanti", "Inserisci il nome del dipendente.")
            return

        nome_default = f"Riepilogo_completo_{self.mese_busta}_{self.anno_busta}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Salva Report PDF", nome_default, "PDF Files (*.pdf)")
        if not file_path:
            return

        r_f = self._ultimo_calc_ferie
        r_p = self._ultimo_calc_par

        def tr(label: str, r: Dict[str, float]) -> str:
            return (f"<tr><td><b>{label}</b></td>"
                    f"<td>{utils.format_ore_decimali(r.get('diritto', 0))}</td>"
                    f"<td>{utils.format_ore_decimali(r.get('res_ap_iniziale', r.get('res_ap', 0)))}</td>"
                    f"<td>{utils.format_ore_decimali(r.get('ap_scalato_anno_precedente', 0))}</td>"
                    f"<td>{utils.format_ore_decimali(r.get('maturato', 0))}</td>"
                    f"<td>{utils.format_ore_decimali(r.get('goduto_tot', 0))}</td>"
                    f"<td>{utils.format_ore_decimali(r.get('res_ap_netto', 0))}</td>"
                    f"<td class='s'>{utils.format_ore_decimali(r.get('saldo', 0))}</td>"
                    f"<td>{utils.format_ore_decimali(r.get('presunto_fine_anno', 0))}</td></tr>")

        storico_rows = []
        for item in self._assenze_effettive_e_programmate():
            origine = item.get("origine", "Storico")
            is_cal = self.dm.calendario.is_collettivo(item["data"])
            if origine == "Calendario":
                tipo_display = f"{item['tipo']} (Calendario)"
            elif is_cal:
                tipo_display = f"{item['tipo']} (Cal)"
            else:
                tipo_display = item["tipo"]

            storico_rows.append(
                "<tr>"
                f"<td>{html.escape(item['data'].toString(config.DATE_FORMAT_DISPLAY))}</td>"
                f"<td>{html.escape(tipo_display)}</td>"
                f"<td>{html.escape(utils.format_ore_decimali(float(item['ore'])))}</td>"
                f"<td>{html.escape(origine)}</td>"
                "</tr>"
            )
        if not storico_rows:
            storico_rows.append('<tr><td colspan="4">Nessuna assenza registrata.</td></tr>')
        storico_html = "\n".join(storico_rows)

        dipendente = html.escape(self.txt_nominativo.text())
        matricola = html.escape(self.txt_matricola.text())

        html_doc = f"""<html><head><style>
            body{{font-family:Arial,sans-serif;font-size:11pt;}}
            h1{{color:#0078d7;font-size:18pt;}}
            h3{{font-size:13pt;margin-top:15pt;margin-bottom:5pt;}}
            p{{font-size:11pt;margin-top:2pt;margin-bottom:2pt;}}
            table{{width:100%;border-collapse:collapse;margin-top:10pt;}}
            th,td{{border:1px solid #ccc;padding:6pt;text-align:center;font-size:10pt;}}
            th{{background-color:#f2f2f2;}}
            .s{{font-weight:bold;}}
            .small{{font-size:9pt;color:#555;}}
        </style></head><body>
            <h1>Report Ferie e PAR</h1>
            <p><b>Data Report:</b> {date.today().strftime("%d/%m/%Y")}</p><hr>
            <h3>Anagrafica</h3>
            <p><b>Dipendente:</b> {dipendente}</p>
            <p><b>Matricola:</b> {matricola}</p>
            <p><b>Data Assunzione:</b> {html.escape(self.date_assunzione.text())}</p>
            <br><h3>Dettaglio saldi</h3>
            <p><b>Nota:</b> valori espressi in ore decimali. 3,5 h = 3 ore e mezza.</p>
            <p><b>Calendario:</b> le date collettive programmate sono gia' scalate dai saldi come giornate intere da 8h, se non gia' presenti nello storico.</p>
            <table>
                <tr><th>Tipo</th><th>Diritto annuo</th><th>Residuo AP iniziale</th><th>AP usato anno prec.</th>
                    <th>Maturato ad oggi</th><th>Usato totale</th><th>Residuo AP rimasto</th><th>Disponibili oggi</th><th>Presunto fine anno</th></tr>
                {tr("FERIE", r_f)}
                {tr("PAR", r_p)}
            </table>

            <br><h3>Storico utilizzi completo</h3>
            <table>
                <tr><th>Data</th><th>Tipo</th><th>Ore</th><th>Origine</th></tr>
                {storico_html}
            </table>

            <br><p class="small">Generato da Gestione Ferie/PAR v{config.APP_VERSION}</p>
        </body></html>"""

        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file_path)
        doc = QTextDocument()
        doc.setHtml(html_doc)
        doc.print(printer)
        QMessageBox.information(self, "Esportazione PDF", f"PDF salvato:\n{file_path}")

    def mostra_info(self) -> None:
        """Visualizza le informazioni sull'autore e sulla versione come richiesto."""
        QMessageBox.about(
            self,
            "Informazioni",
            "<b>Gestione Ferie/PAR</b><br>"
            f"Versione: {config.APP_VERSION}<br>"
            "Autore: <b>Enrico Martini</b><br><br>"
            "Software per il calcolo e la gestione delle ferie e permessi.<br>"
            "Programma redatto per i dipendenti Breton."
        )

    def mostra_guida(self) -> None:
        html = """
        <h2 style="color:#0078d7;">Manuale d'Uso - Gestione Ferie/PAR</h2>
        <p>Calcola e monitora i saldi di Ferie e PAR in modo automatico.</p>
        <h3 style="color:#333;">Calendario</h3>
        <p>Incolla la mail aziendale. Il programma estrarrà le date collettive automaticamente, anche con liste multiple.</p>
        <h3 style="color:#333;">Importazione Buste</h3>
        <p>Estrae i Residui AP e importa le singole giornate direttamente dai PDF Zucchetti.</p>
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Guida Utente")
        dlg.resize(600, 400)
        lay = QVBoxLayout(dlg)
        tb = QTextBrowser()
        tb.setHtml(html)
        lay.addWidget(tb)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(dlg.accept)
        lay.addWidget(bb)
        dlg.exec()