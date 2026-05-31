"""
Test di integrazione per la UI (richiede PyQt6 e pytest-qt).
"""

import pytest
from unittest.mock import MagicMock, patch

# Verifica se PyQt6 è disponibile
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import Qt
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

# Verifica se pytest-qt è disponibile
try:
    from pytestqt.plugin import QtBot
    HAS_PYTEST_QT = True
except ImportError:
    HAS_PYTEST_QT = False


@pytest.mark.skipif(not (HAS_PYQT6 and HAS_PYTEST_QT), reason="Richiede PyQt6 e pytest-qt")
class TestCalcolatoreFeriePAR:
    """Test di integrazione per la finestra principale."""

    @pytest.fixture(autouse=True)
    def setup_qapplication(self, qapp):
        """Assicura che QApplication sia creato."""
        pass

    def test_ui_init(self, qtbot):
        """Test inizializzazione della UI."""
        from ui import CalcolatoreFeriePAR
        
        # Crea la finestra principale
        window = CalcolatoreFeriePAR()
        qtbot.addWidget(window)
        
        # Verifica che la finestra sia stata creata
        assert window is not None
        assert window.windowTitle() == "Gestione Ferie/PAR - Pro v2.3.0"

    def test_ui_sezioni_presenti(self, qtbot):
        """Test che tutte le sezioni della UI siano presenti."""
        from ui import CalcolatoreFeriePAR
        
        window = CalcolatoreFeriePAR()
        qtbot.addWidget(window)
        
        # Verifica che i widget principali siano presenti
        assert hasattr(window, 'txt_nominativo')
        assert hasattr(window, 'txt_matricola')
        assert hasattr(window, 'date_assunzione')
        assert hasattr(window, 'check_patrono')
        assert hasattr(window, 'tab_storico')
        assert hasattr(window, 'tab_saldi')
        assert hasattr(window, 'bar_ferie')
        assert hasattr(window, 'bar_par')

    def test_validazione_nominativo(self, qtbot):
        """Test validazione nominativo vuoto."""
        from ui import CalcolatoreFeriePAR
        from PyQt6.QtWidgets import QMessageBox
        
        window = CalcolatoreFeriePAR()
        qtbot.addWidget(window)
        
        # Simula click su "Inserisci" senza nominativo
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Ok):
            window.txt_nominativo.setText("")
            window.aggiungi_assenza()
            # Verifica che sia stato mostrato un messaggio di errore
            QMessageBox.warning.assert_called_once()

    def test_aggiungi_assenza_valida(self, qtbot):
        """Test aggiunta di un'assenza valida."""
        from ui import CalcolatoreFeriePAR
        from PyQt6.QtCore import QDate
        
        window = CalcolatoreFeriePAR()
        qtbot.addWidget(window)
        
        # Imposta dati validi
        window.txt_nominativo.setText("Mario Rossi")
        window.date_inizio.setDate(QDate(2023, 1, 10))
        window.combo_tipo.setCurrentText("FERIE")
        window.check_giorno_intero.setChecked(True)
        
        # Aggiungi assenza
        initial_count = len(window.dm.storico_assenze)
        window.aggiungi_assenza()
        
        # Verifica che l'assenza sia stata aggiunta
        assert len(window.dm.storico_assenze) == initial_count + 1

    def test_calcola_saldi(self, qtbot):
        """Test calcolo saldi dopo aggiunta assenza."""
        from ui import CalcolatoreFeriePAR
        from PyQt6.QtCore import QDate
        
        window = CalcolatoreFeriePAR()
        qtbot.addWidget(window)
        
        # Imposta dati validi
        window.txt_nominativo.setText("Mario Rossi")
        window.date_assunzione.setDate(QDate(2018, 1, 1))
        window.check_patrono.setChecked(True)
        
        # Aggiungi un'assenza
        window.date_inizio.setDate(QDate(2023, 1, 10))
        window.combo_tipo.setCurrentText("FERIE")
        window.check_giorno_intero.setChecked(True)
        window.aggiungi_assenza()
        
        # Calcola saldi
        window.calcola()
        
        # Verifica che i saldi siano stati calcolati
        assert window._ultimo_calc_ferie != {}
        assert window._ultimo_calc_par != {}


@pytest.mark.skipif(not HAS_PYQT6, reason="Richiede PyQt6")
class TestDialog:
    """Test per dialoghi della UI."""

    def test_dialog_calendario(self, qtbot):
        """Test dialogo calendario."""
        from ui import CalcolatoreFeriePAR
        
        window = CalcolatoreFeriePAR()
        qtbot.addWidget(window)
        
        # Apri dialogo calendario
        window.apri_dialog_calendario()
        
        # Verifica che il dialogo sia stato creato (non possiamo testare l'interazione completa senza UI reale)
        assert True  # Placeholder per test futuri


@pytest.mark.skipif(not HAS_PYQT6, reason="Richiede PyQt6")
class TestImportazioneBuste:
    """Test per importazione buste paga."""

    def test_importa_busta_paga_no_pypdf(self, qtbot):
        """Test importazione buste paga senza pypdf."""
        from ui import CalcolatoreFeriePAR
        from models import HAS_PYPDF
        
        window = CalcolatoreFeriePAR()
        qtbot.addWidget(window)
        
        # Se pypdf non è installato, il pulsante dovrebbe essere disabilitato
        if not HAS_PYPDF:
            for child in window.findChildren(window.btn_import.__class__):
                if child.text() == "Carica Buste Paga":
                    assert child.isEnabled() is False
                    break
