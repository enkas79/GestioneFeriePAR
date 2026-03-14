"""
Layer di Presentazione (UI).
Costruisce la finestra grafica utilizzando le classi di PyQt6.
"""

import os
from datetime import date
from typing import Dict, Tuple

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
            QTableWidget { gridline-color: #ddd; font-size: 13px;
                           alternate-background-color: #f9f9f9; }
            QHeaderView::section { background-color: #e0e0e0; padding: 4px;
                                   border: 1px solid #ccc; font-weight: bold; }
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

        a_pdf = QAction("Esporta in PDF  (Ctrl+P)", self)
        a_pdf.triggered.connect(self.stampa_report)
        a_csv = QAction("Esporta storico CSV", self)
        a_csv.triggered.connect(self.esporta_csv)

        file_menu.addAction(a_pdf)
        file_menu.addAction(a_csv)
        file_menu.addSeparator()

        a_reset = QAction("Reset Dati", self)
        a_reset.triggered.connect(self.reset_dati)
        file_menu.addAction(a_reset)

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
                f"Aggiunte {date_trovate} date valide al Calendario Collettivo."
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
        grid.addWidget(QLabel("Ore (es 3,30):"), 1, 3)
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
        self.tab_storico.setHorizontalHeaderLabels(["Data", "Tipo", "Ore"])
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

        group_saldi = QGroupBox("Saldi e Contatori (Calcolo Autonomo)")
        vbox_saldi = QVBoxLayout()

        hbox_hdr = QHBoxLayout()
        lbl_fifo = QLabel("Maturato automatico su mesi chiusi.")
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
        self.tab_saldi.setColumnCount(7)
        self.tab_saldi.setHorizontalHeaderLabels([
            "Tipo", "Diritto", "Res.AP", "Maturato", "Goduto", "Res.Netto", "SALDO TOT"
        ])
        self.tab_saldi.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tab_saldi.verticalHeader().setVisible(False)
        self.tab_saldi.setRowCount(2)
        self.tab_saldi.setItem(0, 0, QTableWidgetItem(config.TIPO_FERIE))
        self.tab_saldi.setItem(1, 0, QTableWidgetItem(config.TIPO_PAR))
        vbox_saldi.addWidget(self.tab_saldi)
        vbox_saldi.addSpacing(10)

        lbl_f = QLabel("Disponibilità Ferie:")
        lbl_f.setStyleSheet("font-weight: bold;")
        self.bar_ferie = QProgressBar()
        self.bar_ferie.setTextVisible(True)
        self.bar_ferie.setFormat("%v ore")

        lbl_p = QLabel("Disponibilità PAR:")
        lbl_p.setStyleSheet("font-weight: bold;")
        self.bar_par = QProgressBar()
        self.bar_par.setTextVisible(True)
        self.bar_par.setFormat("%v ore")

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
        anni = sorted({item["data"].year() for item in self.dm.storico_assenze}, reverse=True)
        self.combo_filtro_anno.blockSignals(True)
        self.combo_filtro_anno.clear()
        self.combo_filtro_anno.addItem("Tutti")
        for a in anni:
            self.combo_filtro_anno.addItem(str(a))
        self.combo_filtro_anno.blockSignals(False)

    def aggiorna_tabella_storico(self) -> None:
        filtro = self.combo_filtro_anno.currentText()
        self.tab_storico.setRowCount(0)

        for item in self.dm.storico_assenze:
            if filtro != "Tutti" and str(item["data"].year()) != filtro:
                continue

            row = self.tab_storico.rowCount()
            self.tab_storico.insertRow(row)

            is_cal = self.dm.calendario.is_collettivo(item["data"])
            tipo_display = f"{item['tipo']} (Cal)" if is_cal else item["tipo"]

            it_data = QTableWidgetItem(item["data"].toString(config.DATE_FORMAT_DISPLAY))
            it_tipo = QTableWidgetItem(tipo_display)
            it_ore = QTableWidgetItem(f"{item['ore']:.2f}")

            if is_cal:
                color = QColor("#e8f4fd")
                it_data.setBackground(color)
                it_tipo.setBackground(color)
                it_ore.setBackground(color)
                it_tipo.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                it_tipo.setForeground(QColor("#005a9e"))

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
                    d = QDate.fromString(i_data.text(), config.DATE_FORMAT_DISPLAY)
                    t = i_tipo.text().replace(" (Cal)", "")
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

        for x in self.dm.storico_assenze:
            is_cal = self.dm.calendario.is_collettivo(x["data"])
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

        self._ultimo_calc_ferie = self.calc.fifo_avanzato(sp_ferie, self.dm.res_ap_ferie, mat_f, god_f_normale,
                                                          god_f_cal)
        self._ultimo_calc_par = self.calc.fifo_avanzato(sp_par, self.dm.res_ap_par, mat_p, god_p_normale, god_p_cal)

        self._aggiorna_riga(0, self._ultimo_calc_ferie, self.bar_ferie, config.TIPO_FERIE)
        self._aggiorna_riga(1, self._ultimo_calc_par, self.bar_par, config.TIPO_PAR)

    def _aggiorna_riga(self, row: int, r: Dict[str, float], bar: QProgressBar, tipo: str) -> None:
        self.tab_saldi.setItem(row, 1, QTableWidgetItem(f"{r['diritto']:.3f}"))
        self.tab_saldi.setItem(row, 2, QTableWidgetItem(f"{r['res_ap']:.3f}"))
        self.tab_saldi.setItem(row, 3, QTableWidgetItem(f"{r['maturato']:.3f}"))
        self.tab_saldi.setItem(row, 4, QTableWidgetItem(f"{r['goduto_tot']:.3f}"))

        it_ap = QTableWidgetItem(f"{r['res_ap_netto']:.3f}")
        if r["res_ap_netto"] == 0 and r["res_ap"] > 0:
            it_ap.setForeground(QColor("orange"))
        elif r["res_ap_netto"] > 0:
            it_ap.setForeground(QColor("blue"))
        self.tab_saldi.setItem(row, 5, it_ap)

        it_s = QTableWidgetItem(f"{r['saldo']:.3f}")
        it_s.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        it_s.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        it_s.setForeground(QColor("#d9534f") if r["saldo"] < 0 else QColor("#5cb85c"))
        self.tab_saldi.setItem(row, 6, it_s)

        totale = max(r["res_ap"] + r["diritto"], 1.0)
        sval = max(int(r["saldo"]), 0)
        if r["saldo"] < 0:
            style = "QProgressBar::chunk { background-color: #d9534f; }"
        elif r["saldo"] < 40:
            style = "QProgressBar::chunk { background-color: #f0ad4e; }"
        else:
            style = "QProgressBar::chunk { background-color: #5cb85c; }"

        bar.setRange(0, int(totale))
        bar.setValue(sval)
        bar.setStyleSheet(style)

        if r["saldo"] < 0:
            self.lbl_avviso.setText(f"⚠️ Attenzione: saldo {tipo} negativo ({r['saldo']:.3f} ore)!")
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

        nome_default = f"Riepilogo_{self.mese_busta}_{self.anno_busta}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Salva Report PDF", nome_default, "PDF Files (*.pdf)")
        if not file_path:
            return

        r_f = self._ultimo_calc_ferie
        r_p = self._ultimo_calc_par

        def tr(label: str, r: Dict[str, float]) -> str:
            return (f"<tr><td><b>{label}</b></td>"
                    f"<td>{r.get('diritto', 0):.3f}</td>"
                    f"<td>{r.get('res_ap', 0):.3f}</td>"
                    f"<td>{r.get('maturato', 0):.3f}</td>"
                    f"<td>{r.get('goduto_tot', 0):.3f}</td>"
                    f"<td class='s'>{r.get('saldo', 0):.3f}</td></tr>")

        html = f"""<html><head><style>
            body{{font-family:Arial,sans-serif;font-size:11pt;}}
            h1{{color:#0078d7;font-size:18pt;}}
            h3{{font-size:13pt;margin-top:15pt;margin-bottom:5pt;}}
            p{{font-size:11pt;margin-top:2pt;margin-bottom:2pt;}}
            table{{width:100%;border-collapse:collapse;margin-top:10pt;}}
            th,td{{border:1px solid #ccc;padding:6pt;text-align:center;font-size:10pt;}}
            th{{background-color:#f2f2f2;}}
            .s{{font-weight:bold;}}
        </style></head><body>
            <h1>Report Ferie e PAR</h1>
            <p><b>Data Report:</b> {date.today().strftime("%d/%m/%Y")}</p><hr>
            <h3>Anagrafica</h3>
            <p><b>Dipendente:</b> {self.txt_nominativo.text()}</p>
            <p><b>Matricola:</b> {self.txt_matricola.text()}</p>
            <p><b>Data Assunzione:</b> {self.date_assunzione.text()}</p>
            <br><h3>Dettaglio Saldi:</h3><br>
            <table>
                <tr><th>Tipo</th><th>Diritto Annuo</th><th>Residuo AP</th>
                    <th>Maturato</th><th>Goduto Totale</th><th>SALDO FINALE</th></tr>
                {tr("FERIE", r_f)}
                {tr("PAR", r_p)}
            </table><br><br>
            <p style="font-size:9pt;color:#555;">Generato da Gestione Ferie/PAR v{config.APP_VERSION}</p>
        </body></html>"""

        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file_path)
        doc = QTextDocument()
        doc.setHtml(html)
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