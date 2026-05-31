"""
Configurazione globale per pytest.
"""

import sys
import os
from datetime import date

# Aggiungi la root del progetto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa il mock per PyQt6 **prima** di qualsiasi altro modulo
import mock_pyqt6  # noqa: F401

# Ora PyQt6 è mockato, possiamo importare i moduli del progetto
from unittest.mock import MagicMock

# Crea mock per PyQt6 se non è disponibile
try:
    from PyQt6.QtCore import QDate, Qt
    from PyQt6.QtGui import QFont, QColor
except ImportError:
    # Se PyQt6 non è installato, crea mock
    QDate = MagicMock()
    Qt = MagicMock()
    QFont = MagicMock()
    QColor = MagicMock()
    
    # Simula QDate
    def create_qdate(year, month, day):
        mock = MagicMock()
        mock.year.return_value = year
        mock.month.return_value = month
        mock.day.return_value = day
        mock.toString.return_value = f"{year:04d}-{month:02d}-{day:02d}"
        mock.isValid.return_value = True
        mock.dayOfWeek.return_value = (date(year, month, day).weekday() + 1) % 7  # 0=Lun, 6=Dom
        return mock
    
    QDate.fromString = MagicMock(side_effect=lambda s, fmt: create_qdate(2023, 1, 1))
    QDate.currentDate = MagicMock(return_value=create_qdate(date.today().year, date.today().month, date.today().day))
    
    # Simula Qt.AlignmentFlag
    Qt.AlignmentFlag = MagicMock()
    Qt.AlignmentFlag.AlignCenter = 0
    Qt.AlignmentFlag.AlignLeft = 0
    Qt.AlignmentFlag.AlignRight = 0


# Fixture per dati di test
import pytest


@pytest.fixture
def sample_date():
    """Restituisce una data di esempio."""
    return date(2023, 6, 15)


@pytest.fixture
def sample_assunzione():
    """Restituisce una data di assunzione di esempio."""
    return date(2018, 1, 1)


@pytest.fixture
def sample_ore_zucchetti():
    """Restituisce esempi di stringhe ore da Zucchetti."""
    return [
        "8,00",   # 8 ore
        "3,30",   # 3.5 ore
        "4,50",   # 4.833... ore
        "0,50",   # 0.833... ore
    ]


@pytest.fixture
def sample_assenze():
    """Restituisce un esempio di storico assenze."""
    from unittest.mock import MagicMock
    
    def create_mock_qdate(year, month, day):
        mock = MagicMock()
        mock.year.return_value = year
        mock.month.return_value = month
        mock.day.return_value = day
        mock.toString.return_value = f"{year:04d}-{month:02d}-{day:02d}"
        mock.isValid.return_value = True
        return mock
    
    return [
        {"data": create_mock_qdate(2023, 1, 10), "tipo": "FERIE", "ore": 8.0},
        {"data": create_mock_qdate(2023, 1, 15), "tipo": "PAR", "ore": 4.0},
        {"data": create_mock_qdate(2023, 2, 20), "tipo": "FERIE", "ore": 8.0},
    ]
