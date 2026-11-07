"""
Test per le classi in models.py.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock

import config
from models import (
    CalcolatoreLogica,
    CalendarManager,
    DataManager,
    EncryptionManager,
    BustaPageParser,
    BustaPagaEconomicaParser,
    HAS_PYPDF,
    HAS_CRYPTOGRAPHY,
)


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


class TestUpdateManagerParseVersion:
    """Test per il confronto versioni normalizzato di UpdateManager."""

    def _run_check(self, tag_name):
        import json as _json
        from unittest.mock import patch, MagicMock
        from models import UpdateManager
        payload = _json.dumps({"tag_name": tag_name, "html_url": "http://x"}).encode()
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = payload
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        with patch("urllib.request.urlopen", return_value=resp):
            return UpdateManager.check_for_updates()

    def test_versione_uguale_non_aggiorna(self):
        # Versione remota uguale a quella corrente (letta da version.txt)
        has_update, ver, _ = self._run_check(f"v{config.APP_VERSION}")
        assert has_update is False

    def test_versione_maggiore_aggiorna(self):
        # Patch superiore a quella corrente
        parti = [int(x) for x in config.APP_VERSION.split(".")]
        tag = f"v{parti[0]}.{parti[1]}.{parti[2] + 1}"
        has_update, ver, _ = self._run_check(tag)
        assert has_update is True
        assert ver == tag

    def test_versione_minore_piu_corta_non_falsa_positiva(self):
        # "vX.Y" con minor superiore deve essere > "X.Y.Z" (normalizzazione a 3 componenti)
        parti = [int(x) for x in config.APP_VERSION.split(".")]
        tag = f"v{parti[0]}.{parti[1] + 1}"
        has_update, _, _ = self._run_check(tag)
        assert has_update is True


class TestCalcolatoreLogicaDataRiferimento:
    """Test deterministici per calcola_spettanze con data_riferimento."""

    def test_spettanze_con_data_riferimento_fissa(self):
        from datetime import date as _date
        sp_f, sp_p = CalcolatoreLogica.calcola_spettanze(
            _date(2018, 1, 1), True, data_riferimento=_date(2023, 6, 15)
        )
        assert sp_f == 168.0
        assert sp_p == 104.0

    def test_spettanze_18_anni_con_data_riferimento(self):
        from datetime import date as _date
        # Anzianita' misurata dal 1/1/2008: al 2030 sono 22 anni -> bonus 40h
        sp_f, _ = CalcolatoreLogica.calcola_spettanze(
            _date(2000, 1, 1), False, data_riferimento=_date(2030, 1, 1)
        )
        assert sp_f == 200.0


class TestDataManagerExport:
    """Test per esporta_csv e salvataggio atomico."""

    def test_esporta_csv_formato_italiano(self, tmp_path):
        dm = DataManager()
        dm.nominativo = "Mario Rossi"
        dm.storico_assenze.append({"data": create_mock_qdate(2023, 1, 10), "tipo": "FERIE", "ore": 3.5})
        path = str(tmp_path / "out.csv")
        assert dm.esporta_csv(path) is True
        contenuto = open(path, encoding='utf-8').read()
        assert contenuto.splitlines()[0] == "Data;Tipo;Ore;Info"
        assert "3,50" in contenuto

    def test_salva_su_file_atomico(self, tmp_path):
        import os
        dm = DataManager()
        path = str(tmp_path / "db.json")
        ok, err = dm.salva_su_file(path)
        assert ok is True, err
        import json
        with open(path, encoding='utf-8') as f:
            payload = json.load(f)
        assert payload["versione_app"] == config.APP_VERSION
        # Nessun file temporaneo residuo dopo scrittura atomica
        residui = [f for f in os.listdir(tmp_path) if f.startswith('.tmp_')]
        assert residui == []

    def test_assenze_effettive_e_programmate_pubblico(self):
        dm = DataManager()
        dm.storico_assenze.append({"data": create_mock_qdate(2023, 1, 10), "tipo": "FERIE", "ore": 8.0})
        righe = dm.assenze_effettive_e_programmate()
        assert len(righe) == 1
        assert righe[0]["origine"] in ("Storico", "Programmata")


TESTO_BUSTA_ECONOMICA = """\
GENNAIO 2026
       1218 MARTINI ENRICO                          MRTNRC79R31C111I           C3   103265
     1218   31/10/1979 01/07/2004                       Operaio                           C3
                                    73 50  22 00 176 00  24 00                24   5
     Minimo retr.          2158,26 Scatti                148,20
CODICE DESCRIZIONE VOCE ORE/GIORNI IMPORTO UNITARIO IMPORTI FIGURATI C O M P E T E N Z E T R A T T E N U T E
     AA245  Retribuzione               26,000  102,12154                  2655,16
     F2105  Ferie godute *             24,000   15,34775       368,35
     TN100  Tratt.sindacale                                                             18,44
     W99901 Ore Ordinarie              73,500   15,34775      1128,06
     W99961 Imp. Previd. progressivo                          2674,00
     ---------------------------------------- Imponibili     Aliquote  Competenze  Trattenute
     005    INPS-FPLD/IVS      -c/DIP            2687,00        9,190                  246,94
     F39    COMETA             -c/DIP            2158,26        1,200                   25,90
     F40    COMETA             -c/AZI            2158,26       43,170
     ----------------------------------------  Ctb. ded. Ctb.non ded. -----------------------
     000039 COMETA                                 69,07
     Addizionali ----------------------- Anno Impon/Rata   Figurative  Competenze  Trattenute
     001    Addizionale regionale        2025      38,99       350,91                   38,99
     002    Addizionale comunale         2026   31698,89        34,95
     Imposta sul T.F.R dal 01/01/2001 -------- Imp.lordi  Aliq./Detr.  Detrazioni  Trattenute
     TFR901 Imponibile TFR                                    2655,16
     W90003 TFR COMETA                            100,00       183,24
     CREDITO TREVIGIANO - BANCA DI CREDIT Emolumenti correnti             2406,35      560,77
                                                                                  ****1953,00
"""


class TestBustaPagaEconomicaParser:
    """Test per BustaPagaEconomicaParser (parte economica, separata da ferie/PAR)."""

    def test_parse_testo_vuoto(self):
        parser = BustaPagaEconomicaParser()
        risultato = parser.parse("")
        assert risultato["mese"] is None
        assert risultato["anno"] is None
        assert risultato["voci"] == []
        assert risultato["totali"] == {}

    def test_parse_mese_anno(self):
        parser = BustaPagaEconomicaParser()
        risultato = parser.parse(TESTO_BUSTA_ECONOMICA)
        assert risultato["mese"] == 1
        assert risultato["anno"] == 2026
        assert risultato["mese_str"] == "Gennaio"

    def test_parse_anagrafica(self):
        parser = BustaPagaEconomicaParser()
        ana = parser.parse(TESTO_BUSTA_ECONOMICA)["anagrafica"]
        assert ana["matricola"] == "1218"
        assert ana["nominativo"] == "MARTINI ENRICO"
        assert ana["codice_fiscale"] == "MRTNRC79R31C111I"
        assert ana["data_assunzione"] == "01/07/2004"
        assert ana["qualifica"] == "Operaio"
        assert ana["livello"] == "C3"
        assert ana["minimo_retributivo"] == 2158.26
        assert ana["ral_stimata"] == round(2158.26 * config.MENSILITA_ANNUE, 2)
        assert ana["ore_lavorate"] == 176.0
        assert ana["paga_oraria"] == 15.34775

    def test_parse_voci_categorie(self):
        parser = BustaPagaEconomicaParser()
        voci = parser.parse(TESTO_BUSTA_ECONOMICA)["voci"]
        per_codice = {v["codice"]: v for v in voci}
        assert per_codice["AA245"]["categoria"] == "competenza"
        assert per_codice["AA245"]["importo"] == 2655.16
        assert per_codice["F2105"]["ore"] == 24.0
        assert per_codice["TN100"]["categoria"] == "trattenuta"
        assert per_codice["TN100"]["importo"] == 18.44
        assert per_codice["W99961"]["categoria"] == "figurativo"
        # I ratei ferie/PAR e i codici TFR non devono finire nella parte economica
        assert all(not v["descrizione"].startswith(":") for v in voci)
        assert "TFR901" not in per_codice and "W90003" not in per_codice

    def test_parse_contributi(self):
        parser = BustaPagaEconomicaParser()
        risultato = parser.parse(TESTO_BUSTA_ECONOMICA)
        dip = {c["codice"]: c for c in risultato["contributi_dipendente"]}
        assert dip["005"]["imponibile"] == 2687.00
        assert dip["005"]["aliquota"] == 9.19
        assert dip["005"]["importo"] == 246.94
        assert dip["F39"]["importo"] == 25.90
        azi = {c["codice"]: c for c in risultato["contributi_azienda"]}
        assert azi["F40"]["aliquota"] == 43.17

    def test_parse_addizionali_tfr_totali(self):
        parser = BustaPagaEconomicaParser()
        risultato = parser.parse(TESTO_BUSTA_ECONOMICA)
        add = {a["descrizione"]: a["importo"] for a in risultato["addizionali"]}
        assert add["Addizionale regionale"] == 38.99
        # Conguaglio con due soli numeri: l'importo e' l'ultimo numero (34,95)
        assert add["Addizionale comunale"] == 34.95
        assert risultato["tfr"]["imponibile"] == 2655.16
        assert risultato["tfr"]["quota"] == 183.24
        assert risultato["totali"]["tot_competenze"] == 2406.35
        assert risultato["totali"]["tot_trattenute"] == 560.77
        assert risultato["totali"]["netto"] == 1953.00
        assert risultato["oneri_ctb"][0]["importo"] == 69.07


class TestDataManagerEconomico:
    """Test persistenza della parte economica in DataManager (separata da ferie/PAR)."""

    def _record(self, anno=2026, mese=1):
        return {
            "anno": anno, "mese": mese, "mese_str": "Gennaio",
            "anagrafica": {"minimo_retributivo": 2158.26, "ral_stimata": 28057.38},
            "voci": [], "contributi_dipendente": [], "contributi_azienda": [],
            "addizionali": [], "oneri_ctb": [], "tfr": {"quota": 183.24},
            "totali": {"tot_competenze": 2406.35, "tot_trattenute": 560.77, "netto": 1953.00},
        }

    def test_upsert_inserisce_e_aggiorna(self):
        dm = DataManager()
        assert dm.upsert_record_economico(self._record()) is True
        assert dm.upsert_record_economico(self._record(mese=2)) is True
        # Stesso mese: aggiornamento, non duplicato
        rec = self._record()
        rec["totali"]["netto"] = 2000.0
        assert dm.upsert_record_economico(rec) is False
        assert len(dm.storico_economico) == 2
        assert dm.storico_economico[0]["totali"]["netto"] == 2000.0

    def test_rimuovi_record(self):
        dm = DataManager()
        dm.upsert_record_economico(self._record())
        assert dm.rimuovi_record_economico(2026, 1) is True
        assert dm.storico_economico == []
        assert dm.rimuovi_record_economico(2026, 1) is False

    def test_payload_roundtrip_economico(self):
        dm = DataManager()
        dm.upsert_record_economico(self._record())
        payload = dm._crea_payload()
        assert "storico_economico" in payload

        dm2 = DataManager()
        dm2._applica_payload(payload)
        assert len(dm2.storico_economico) == 1
        assert dm2.storico_economico[0]["totali"]["netto"] == 1953.00

    def test_retrocompatibilita_payload_senza_economico(self):
        dm = DataManager()
        payload = {"nominativo": "Mario Rossi", "storico_assenze": [], "testo_mail_calendario": ""}
        dm._applica_payload(payload)
        assert dm.storico_economico == []

    def test_reset_azzera_economico(self):
        dm = DataManager()
        dm.upsert_record_economico(self._record())
        dm.reset()
        assert dm.storico_economico == []
