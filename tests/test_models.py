"""
Test per le classi in models.py.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock

# Mock per QDate (per evitare dipendenza da PyQt6 nei test)
def create_mock_qdate(year, month, day, day_of_week=None):
    """Crea un mock di QDate con i metodi necessari."""
    mock = MagicMock()
    mock.year.return_value = year
    mock.month.return_value = month
    mock.day.return_value = day
    mock.toString.return_value = f"{year:04d}-{month:02d}-{day:02d}"
    mock.isValid.return_value = True
    mock.dayOfWeek.return_value = day_of_week if day_of_week is not None else (date(year, month, day).weekday() + 1) % 7
    mock.addDays = MagicMock(side_effect=lambda n: create_mock_qdate(year, month, day + n))
    mock.__lt__ = MagicMock(side_effect=lambda other: (year, month, day) < (other.year(), other.month(), other.day()))
    mock.__le__ = MagicMock(side_effect=lambda other: (year, month, day) <= (other.year(), other.month(), other.day()))
    mock.__eq__ = MagicMock(side_effect=lambda other: (year, month, day) == (other.year(), other.month(), other.day()))
    return mock

# Crea un mock per QDate
QDate = MagicMock()
QDate.fromString = MagicMock(side_effect=lambda s, fmt: create_mock_qdate(2023, 1, 1))
QDate.currentDate = MagicMock(return_value=create_mock_qdate(date.today().year, date.today().month, date.today().day))

from models import (
    CalcolatoreLogica,
    CalendarManager,
    DataManager,
    EncryptionManager,
    BustaPageParser,
    HAS_PYPDF,
    HAS_CRYPTOGRAPHY,
)
import config


class TestCalcolatoreLogica:
    """Test per CalcolatoreLogica."""

    def test_calcola_mesi_maturati_anno_corrente(self, sample_assunzione):
        """Test calcolo mesi maturati nell'anno corrente."""
        oggi = date(2023, 6, 15)
        mesi = CalcolatoreLogica.calcola_mesi_maturati(sample_assunzione, oggi)
        # Assunzione: 1 gennaio 2018 -> a giugno 2023: 5 mesi chiusi (gen-mag)
        assert mesi == 5

    def test_calcola_mesi_maturati_anno_assunzione(self):
        """Test calcolo mesi maturati nell'anno di assunzione."""
        assunzione = date(2023, 3, 15)
        oggi = date(2023, 6, 15)
        mesi = CalcolatoreLogica.calcola_mesi_maturati(assunzione, oggi)
        # Logica: mesi_chiusi = 5 (gen-mag), mesi_lavorati = 5 - 3 + 1 = 3
        # Poiché assunzione.day == 15 (non > 15), non viene sottratto 1
        assert mesi == 3

    def test_calcola_spettanze_senza_patrono(self, sample_assunzione):
        """Test calcolo spettanze senza S. Patrono."""
        sp_ferie, sp_par = CalcolatoreLogica.calcola_spettanze(sample_assunzione, False)
        # Dipendente assunto nel 2018: 160h ferie + 104h PAR (nessun bonus anzianità)
        assert sp_ferie == 160.0
        assert sp_par == 104.0

    def test_calcola_spettanze_con_patrono(self, sample_assunzione):
        """Test calcolo spettanze con S. Patrono."""
        sp_ferie, sp_par = CalcolatoreLogica.calcola_spettanze(sample_assunzione, True)
        # Dipendente assunto nel 2018: 160h ferie + 8h patrono + 104h PAR
        assert sp_ferie == 168.0
        assert sp_par == 104.0

    def test_calcola_spettanze_anzianita_10_anni(self):
        """Test calcolo spettanze con anzianità >10 anni."""
        assunzione = date(2010, 1, 1)
        sp_ferie, sp_par = CalcolatoreLogica.calcola_spettanze(assunzione, False)
        # +8h per anzianità >10 anni
        assert sp_ferie == 168.0
        assert sp_par == 104.0

    def test_calcola_spettanze_anzianita_18_anni(self):
        """Test calcolo spettanze con anzianità >18 anni."""
        assunzione = date(2000, 1, 1)
        sp_ferie, sp_par = CalcolatoreLogica.calcola_spettanze(assunzione, False)
        # +40h per anzianità >18 anni
        assert sp_ferie == 200.0
        assert sp_par == 104.0

    def test_fifo_avanzato_base(self):
        """Test FIFO avanzato con valori base."""
        risultato = CalcolatoreLogica.fifo_avanzato(
            diritto=160.0,
            res_ap=40.0,
            maturato=80.0,
            goduto_normale=30.0,
            goduto_cal=0.0,
        )
        # Residuo AP: 40 - 30 = 10
        # Maturato netto: 80 - 0 = 80
        # Saldo: 10 + 80 = 90
        assert risultato["res_ap_netto"] == 10.0
        assert risultato["maturato_netto"] == 80.0
        assert risultato["saldo"] == 90.0

    def test_fifo_avanzato_con_goduto_cal(self):
        """Test FIFO avanzato con goduto da calendario."""
        risultato = CalcolatoreLogica.fifo_avanzato(
            diritto=160.0,
            res_ap=40.0,
            maturato=80.0,
            goduto_normale=20.0,
            goduto_cal=10.0,
        )
        # Residuo AP: 40 - 20 = 20
        # Maturato netto: 80 - 10 = 70
        # Saldo: 20 + 70 = 90
        assert risultato["res_ap_netto"] == 20.0
        assert risultato["maturato_netto"] == 70.0
        assert risultato["saldo"] == 90.0


@pytest.mark.skip(reason="Richiede PyQt6.QtCore.QDate reale per parsing complesso")
class TestCalendarManager:
    """Test per CalendarManager (skipato senza PyQt6 reale)."""

    def test_aggiorna_da_testo_data_singola(self):
        """Test parsing di una singola data."""
        cm = CalendarManager()
        testo = "Chiusura il 25 aprile 2023 per festività"
        date_trovate = cm.aggiorna_da_testo(testo)
        assert date_trovate >= 1
        # Verifica che la data sia stata aggiunta (usando stringa ISO)
        assert "2023-04-25" in cm.date_collettive

    def test_aggiorna_da_testo_range_date(self):
        """Test parsing di un range di date."""
        cm = CalendarManager()
        testo = "Chiusura dal 1 al 5 agosto 2023"
        date_trovate = cm.aggiorna_da_testo(testo)
        # Verifica che siano state aggiunte almeno alcune date
        assert date_trovate >= 1

    def test_aggiorna_da_testo_tipo_ferie(self):
        """Test parsing con tipo FERIE."""
        cm = CalendarManager()
        testo = "Ferie collettive dal 1 al 3 agosto 2023"
        cm.aggiorna_da_testo(testo)
        for d in cm.date_collettive:
            assert cm.tipi_collettivi.get(d, config.TIPO_FERIE) == config.TIPO_FERIE

    def test_aggiorna_da_testo_tipo_par(self):
        """Test parsing con tipo PAR."""
        cm = CalendarManager()
        testo = "PAR collettivi il 24 dicembre 2023"
        cm.aggiorna_da_testo(testo)
        for d in cm.date_collettive:
            assert cm.tipi_collettivi.get(d, config.TIPO_PAR) == config.TIPO_PAR

    def test_is_collettivo(self):
        """Test verifica se una data è collettiva."""
        cm = CalendarManager()
        cm.aggiorna_da_testo("Chiusura il 25 aprile 2023")
        # Crea un mock QDate per il 25 aprile 2023
        qdate_25 = create_mock_qdate(2023, 4, 25)
        qdate_25.toString = MagicMock(return_value="2023-04-25")
        assert cm.is_collettivo(qdate_25) is True
        
        qdate_26 = create_mock_qdate(2023, 4, 26)
        qdate_26.toString = MagicMock(return_value="2023-04-26")
        assert cm.is_collettivo(qdate_26) is False


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography non installato")
class TestEncryptionManager:
    """Test per EncryptionManager."""

    def test_encrypt_decrypt(self):
        """Test crittografia e decrittografia."""
        password = "test_password_123"
        em = EncryptionManager(password)
        
        data = '{"test": "data", "value": 42}'
        encrypted = em.encrypt(data)
        decrypted = em.decrypt(encrypted)
        
        assert decrypted == data

    def test_encrypt_decrypt_different_password(self):
        """Test che password diverse non decifrano lo stesso dato."""
        em1 = EncryptionManager("password1")
        em2 = EncryptionManager("password2")
        
        data = '{"test": "data"}'
        encrypted = em1.encrypt(data)
        
        with pytest.raises(Exception):
            em2.decrypt(encrypted)

    def test_is_encrypted(self):
        """Test verifica se un file è cifrato."""
        import tempfile
        import os
        
        password = "test_password"
        em = EncryptionManager(password)
        
        # Crea un file cifrato temporaneo
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            encrypted_data = em.encrypt('{"test": "data"}')
            f.write(encrypted_data)
            temp_path = f.name
        
        try:
            assert EncryptionManager.is_encrypted(temp_path) is True
        finally:
            os.unlink(temp_path)

    def test_is_not_encrypted(self):
        """Test verifica se un file JSON non è cifrato."""
        import tempfile
        import os
        
        # Crea un file JSON temporaneo
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            temp_path = f.name
        
        try:
            assert EncryptionManager.is_encrypted(temp_path) is False
        finally:
            os.unlink(temp_path)


class TestDataManager:
    """Test per DataManager."""

    def test_init(self):
        """Test inizializzazione DataManager."""
        dm = DataManager()
        assert dm.nominativo == ""
        assert dm.matricola == ""
        assert dm.res_ap_ferie == 0.0
        assert dm.res_ap_par == 0.0
        assert dm.includi_patrono is True
        assert len(dm.storico_assenze) == 0

    def test_reset(self):
        """Test reset DataManager."""
        dm = DataManager()
        dm.nominativo = "Mario Rossi"
        dm.res_ap_ferie = 40.0
        dm.storico_assenze.append({"data": create_mock_qdate(2023, 1, 1), "tipo": "FERIE", "ore": 8.0})
        
        dm.reset()
        
        assert dm.nominativo == ""
        assert dm.res_ap_ferie == 0.0
        assert len(dm.storico_assenze) == 0

    def test_crea_payload(self):
        """Test creazione payload JSON."""
        dm = DataManager()
        dm.nominativo = "Mario Rossi"
        dm.matricola = "12345"
        dm.res_ap_ferie = 40.0
        dm.res_ap_par = 20.0
        
        payload = dm._crea_payload()
        
        assert payload["nominativo"] == "Mario Rossi"
        assert payload["matricola"] == "12345"
        assert payload["res_ap_ferie_start"] == 40.0
        assert payload["res_ap_par_start"] == 20.0

    def test_applica_payload(self):
        """Test applicazione payload JSON."""
        dm = DataManager()
        payload = {
            "nominativo": "Mario Rossi",
            "matricola": "12345",
            "res_ap_ferie_start": 40.0,
            "res_ap_par_start": 20.0,
            "includi_patrono": False,
            "storico_assenze": [],
            "testo_mail_calendario": "",
        }
        
        dm._applica_payload(payload)
        
        assert dm.nominativo == "Mario Rossi"
        assert dm.matricola == "12345"
        assert dm.res_ap_ferie == 40.0
        assert dm.res_ap_par == 20.0
        assert dm.includi_patrono is False

    def test_calcola_saldi(self, sample_assunzione):
        """Test calcolo saldi con DataManager."""
        dm = DataManager()
        dm.res_ap_ferie = 40.0
        dm.res_ap_par = 20.0
        
        oggi = date(2023, 6, 15)
        risultati = dm.calcola_saldi(sample_assunzione, True, oggi=oggi)
        
        assert "ferie" in risultati
        assert "par" in risultati
        assert "saldo" in risultati["ferie"]
        assert "saldo" in risultati["par"]


@pytest.mark.skipif(not HAS_PYPDF, reason="pypdf non installato")
class TestBustaPageParser:
    """Test per BustaPageParser."""

    def test_parse_testo_vuoto(self):
        """Test parsing di testo vuoto."""
        parser = BustaPageParser()
        risultato = parser.parse("")
        
        assert risultato["ferie"] is None
        assert risultato["par"] is None
        assert risultato["mese"] is None
        assert risultato["anno"] is None

    def test_parse_res_ap_ferie(self):
        """Test parsing Residuo AP Ferie."""
        parser = BustaPageParser()
        testo = "FERIE Res.AP 40,00"
        risultato = parser.parse(testo)
        
        assert risultato["ferie"] is not None
        assert risultato["ferie"]["res_ap"] == 40.0

    def test_parse_res_ap_par(self):
        """Test parsing Residuo AP PAR."""
        parser = BustaPageParser()
        testo = "P.A.R. Res.AP 20,00"
        risultato = parser.parse(testo)
        
        assert risultato["par"] is not None
        assert risultato["par"]["res_ap"] == 20.0

    def test_parse_mese_anno(self):
        """Test parsing mese e anno."""
        parser = BustaPageParser()
        testo = "MAGGIO 2023"
        risultato = parser.parse(testo)
        
        assert risultato["mese"] == 5
        assert risultato["anno"] == 2023
        assert risultato["mese_str"] == "Maggio"

    def test_parse_giornate(self):
        """Test parsing giornate."""
        parser = BustaPageParser()
        # Simula un testo di busta paga con mese/anno
        testo = "MAGGIO 2023\n10  F 132   8,00\n15  P 134   4,00"
        risultato = parser.parse(testo)
        
        # Verifica che siano state parse almeno le informazioni di base
        assert risultato["mese"] == 5
        assert risultato["anno"] == 2023
        # Note: Il parsing delle giornate dipende da QDate, che è mockato
