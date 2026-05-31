"""
Test per le funzioni di utilità in utils.py.
"""

import pytest
from datetime import date

# Importa il mock per QDate
from mock_pyqt6 import MockQDate

from utils import (
    parse_numero_it,
    hhmm_to_decimal,
    decimal_to_hhmm,
    format_ore_decimali,
    parse_ore_zucchetti,
    is_giorno_festivo,
)


class TestParseNumeroIt:
    """Test per parse_numero_it."""

    def test_parse_numero_it_formato_italiano(self):
        """Test parsing numeri in formato italiano (1.234,56)."""
        assert parse_numero_it("1.234,56") == 1234.56
        assert parse_numero_it("12,50") == 12.50
        assert parse_numero_it("3,5") == 3.5

    def test_parse_numero_it_formato_inglese(self):
        """Test parsing numeri in formato inglese (1,234.56)."""
        assert parse_numero_it("1234.56") == 1234.56
        assert parse_numero_it("12.50") == 12.50

    def test_parse_numero_it_valore_invalido(self):
        """Test parsing di valori non validi."""
        assert parse_numero_it("abc") == 0.0
        assert parse_numero_it("") == 0.0
        assert parse_numero_it("12.34.56") == 0.0


class TestHhmmToDecimal:
    """Test per hhmm_to_decimal."""

    def test_hhmm_to_decimal_intero(self):
        """Test conversione ore intere."""
        assert hhmm_to_decimal(8.0) == 8.0
        assert hhmm_to_decimal(0.0) == 0.0

    def test_hhmm_to_decimal_mezzora(self):
        """Test conversione mezz'ora (3,30 -> 3.5)."""
        assert hhmm_to_decimal(3.30) == 3.5
        assert hhmm_to_decimal(7.30) == 7.5

    def test_hhmm_to_decimal_quarto_ora(self):
        """Test conversione quarto d'ora (3,15 -> 3.25)."""
        assert hhmm_to_decimal(3.15) == 3.25
        assert hhmm_to_decimal(1.45) == 1.75

    def test_hhmm_to_decimal_negativo(self):
        """Test conversione valori negativi."""
        assert hhmm_to_decimal(-3.30) == -3.5


class TestDecimalToHhmm:
    """Test per decimal_to_hhmm."""

    def test_decimal_to_hhmm_intero(self):
        """Test conversione ore intere."""
        assert decimal_to_hhmm(8.0) == 8.0
        assert decimal_to_hhmm(0.0) == 0.0

    def test_decimal_to_hhmm_mezzora(self):
        """Test conversione mezz'ora (3.5 -> 3.30)."""
        assert decimal_to_hhmm(3.5) == 3.30
        assert decimal_to_hhmm(7.5) == 7.30

    def test_decimal_to_hhmm_quarto_ora(self):
        """Test conversione quarto d'ora (3.25 -> 3.15)."""
        assert decimal_to_hhmm(3.25) == 3.15
        assert decimal_to_hhmm(1.75) == 1.45


class TestFormatOreDecimali:
    """Test per format_ore_decimali."""

    def test_format_ore_decimali_intero(self):
        """Test formattazione ore intere."""
        assert format_ore_decimali(8.0) == "8 h"
        assert format_ore_decimali(0.0) == "0 h"

    def test_format_ore_decimali_decimale(self):
        """Test formattazione ore decimali."""
        assert format_ore_decimali(3.5) == "3,5 h"
        assert format_ore_decimali(7.25) == "7,25 h"

    def test_format_ore_decimali_zero(self):
        """Test formattazione zero."""
        assert format_ore_decimali(0.0) == "0 h"


class TestParseOreZucchetti:
    """Test per parse_ore_zucchetti."""

    def test_parse_ore_zucchetti_formato_standard(self):
        """Test parsing ore in formato Zucchetti (8,00 -> 8.0)."""
        assert parse_ore_zucchetti("8,00") == 8.0
        assert parse_ore_zucchetti("3,30") == 3.5
        assert parse_ore_zucchetti("4,50") == pytest.approx(4.833333, rel=1e-3)

    def test_parse_ore_zucchetti_formato_senza_minuti(self):
        """Test parsing ore senza minuti (8 -> 8.0)."""
        assert parse_ore_zucchetti("8") == 8.0


class TestIsGiornoFestivo:
    """Test per is_giorno_festivo."""

    def test_is_giorno_festivo_sabato(self):
        """Test sabato (giorno festivo)."""
        # Sabato: dayOfWeek = 6
        sabato = MockQDate(2023, 6, 17)
        assert is_giorno_festivo(sabato) is True

    def test_is_giorno_festivo_domenica(self):
        """Test domenica (giorno festivo)."""
        # Domenica: dayOfWeek = 0
        domenica = MockQDate(2023, 6, 18)
        assert is_giorno_festivo(domenica) is True

    def test_is_giorno_festivo_feriale(self):
        """Test giorno feriale (non festivo)."""
        # Lunedì: dayOfWeek = 1
        lunedi = MockQDate(2023, 6, 19)
        assert is_giorno_festivo(lunedi) is False

    def test_is_giorno_festivo_natale(self):
        """Test Natale (25 dicembre)."""
        natale = MockQDate(2023, 12, 25)
        assert is_giorno_festivo(natale) is True

    def test_is_giorno_festivo_capodanno(self):
        """Test Capodanno (1 gennaio)."""
        capodanno = MockQDate(2023, 1, 1)
        assert is_giorno_festivo(capodanno) is True

    def test_is_giorno_festivo_pasquetta(self):
        """Test Pasquetta (lunedì dopo Pasqua)."""
        # Pasquetta 2023: 10 aprile (lunedì)
        pasquetta = MockQDate(2023, 4, 10)
        assert is_giorno_festivo(pasquetta) is True

    def test_is_giorno_festivo_ferragosto(self):
        """Test Ferragosto (15 agosto)."""
        # Ferragosto 2023: 15 agosto (martedì)
        ferragosto = MockQDate(2023, 8, 15)
        assert is_giorno_festivo(ferragosto) is True
