"""
Modulo dei modelli e della logica di business.
Gestisce il salvataggio dei dati (DataManager), il calcolo logico dei ratei,
il parsing delle email (CalendarManager), la lettura dei PDF (BustaPageParser)
e il controllo degli aggiornamenti (UpdateManager).
"""

import json
import os
import re
import shutil
import urllib.request
import urllib.error
from datetime import date
from typing import Dict, List, Set, Tuple, Any
from PyQt6.QtCore import QDate

import config
import utils

try:
    from pypdf import PdfReader

    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class UpdateManager:
    """Gestisce il controllo degli aggiornamenti interrogando le API di GitHub Releases."""

    @staticmethod
    def check_for_updates() -> Tuple[bool, str, str]:
        """
        Verifica la presenza di una nuova release su GitHub confrontando i Tag.

        Returns:
            Tuple[bool, str, str]: (Aggiornamento disponibile, Nuova versione, URL della release)
        """
        try:
            # Creiamo la richiesta aggiungendo uno User-Agent (richiesto dalle API GitHub)
            req = urllib.request.Request(config.GITHUB_API_URL, headers={'User-Agent': 'GestioneFeriePAR'})

            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    latest_version = data.get("tag_name", "").strip()

                    if not latest_version:
                        return False, config.APP_VERSION, ""

                    # Funzione interna per estrarre solo i numeri dalla stringa (es. "v1.0.2" -> (1, 0, 2))
                    def parse_version(v: str) -> Tuple[int, ...]:
                        numeri = re.findall(r'\d+', v)
                        return tuple(map(int, numeri)) if numeri else (0,)

                    v_latest = parse_version(latest_version)
                    v_current = parse_version(config.APP_VERSION)

                    # Se la versione su GitHub è maggiore di quella locale
                    if v_latest > v_current:
                        html_url = data.get("html_url", config.GITHUB_RELEASES_URL)
                        return True, latest_version, html_url

        except Exception as e:
            # Silenziamo l'errore per non far crashare l'app in assenza di rete o limiti API
            print(f"Errore controllo aggiornamenti: {e}")

        return False, config.APP_VERSION, ""


class CalendarManager:
    """Gestisce l'estrazione intelligente dei giorni collettivi (Cal) dalle mail."""

    def __init__(self) -> None:
        self.testo_mail: str = ""
        self.date_collettive: Set[str] = set()

    def aggiorna_da_testo(self, testo: str) -> int:
        """
        Analizza il testo della mail e popola il set di date collettive.

        Args:
            testo (str): Testo grezzo copiato dalla mail aziendale.

        Returns:
            int: Numero di giorni lavorativi collettivi identificati.
        """
        self.testo_mail = testo
        self.date_collettive.clear()

        mesi_it: Dict[str, int] = {
            "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
            "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
            "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12
        }

        anno_corrente = date.today().year

        for linea in testo.split('\n'):
            linea_lower = linea.strip().lower()
            if not linea_lower:
                continue

            m_year = re.search(r'\b(20\d{2})\b', linea_lower)
            year_esteso = int(m_year.group(1)) if m_year else anno_corrente

            pat_range = r'da[l]?\s+(?:[a-zì]+\s+)?(\d{1,2})\s*(?:([a-z]+)\s+)?(?:20\d{2}\s+)?a[l]?\s+(?:[a-zì]+\s+)?(\d{1,2})\s+([a-z]+)'
            m_range = re.search(pat_range, linea_lower)

            if m_range:
                d_start_str, m_start_str, d_end_str, m_end_str = m_range.groups()
                m_start_str = m_start_str if m_start_str else m_end_str

                if m_start_str in mesi_it and m_end_str in mesi_it:
                    y_start = year_esteso
                    if mesi_it[m_start_str] == 12 and mesi_it[m_end_str] == 1:
                        y_start = year_esteso - 1

                    start_date = QDate(y_start, mesi_it[m_start_str], int(d_start_str))
                    end_date = QDate(year_esteso, mesi_it[m_end_str], int(d_end_str))

                    if start_date.isValid() and end_date.isValid():
                        curr = start_date
                        while curr <= end_date:
                            if not utils.is_giorno_festivo(curr):
                                self.date_collettive.add(curr.toString(config.DATE_FORMAT_INTERNAL))
                            curr = curr.addDays(1)
                    continue

            mese_trovato = None
            for m, m_int in mesi_it.items():
                if m in linea_lower:
                    mese_trovato = m_int
                    break

            if mese_trovato:
                linea_pulita = re.sub(r'\b\d+\s*(gg|giorni)\b', '', linea_lower)
                giorni = re.findall(r'\b(\d{1,2})\b', linea_pulita)
                for g_str in giorni:
                    try:
                        d_val = int(g_str)
                        if 1 <= d_val <= 31:
                            qdate = QDate(year_esteso, mese_trovato, d_val)
                            if qdate.isValid() and not utils.is_giorno_festivo(qdate):
                                self.date_collettive.add(qdate.toString(config.DATE_FORMAT_INTERNAL))
                    except ValueError:
                        continue

            pattern_numerico = r"\b(\d{1,2})[/\.-](\d{1,2})(?:[/\.-](\d{2,4}))?\b"
            for d_str, m_str, y_str in re.findall(pattern_numerico, linea_lower):
                try:
                    d, m = int(d_str), int(m_str)
                    y = int(y_str) if y_str else year_esteso
                    if y < 100:
                        y += 2000
                    qdate = QDate(y, m, d)
                    if qdate.isValid() and not utils.is_giorno_festivo(qdate):
                        self.date_collettive.add(qdate.toString(config.DATE_FORMAT_INTERNAL))
                except ValueError:
                    continue

        return len(self.date_collettive)

    def is_collettivo(self, qdate: QDate) -> bool:
        """Verifica se una data specifica rientra nei giorni collettivi."""
        return qdate.toString(config.DATE_FORMAT_INTERNAL) in self.date_collettive


class DataManager:
    """Gestisce la persistenza dei dati utente su file JSON locale."""

    def __init__(self) -> None:
        self.calendario = CalendarManager()
        self.nominativo: str = ""
        self.matricola: str = ""
        self.data_assunzione: str = ""
        self.res_ap_ferie: float = 0.0
        self.res_ap_par: float = 0.0
        self.includi_patrono: bool = True
        self.storico_assenze: List[Dict[str, Any]] = []
        self.reset()

    def reset(self) -> None:
        """Resetta in memoria tutti i parametri ai valori di default."""
        self.nominativo = ""
        self.matricola = ""
        self.data_assunzione = QDate.currentDate().addYears(-5).toString(config.DATE_FORMAT_INTERNAL)
        self.res_ap_ferie = 0.0
        self.res_ap_par = 0.0
        self.includi_patrono = True
        self.storico_assenze.clear()
        self.calendario.aggiorna_da_testo("")

    def carica(self) -> bool:
        """Carica i dati utente dal file di salvataggio. Restituisce True se riesce."""
        if not os.path.exists(config.FILE_DATI):
            return False
        try:
            with open(config.FILE_DATI, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            self.nominativo = raw.get("nominativo", "")
            self.matricola = raw.get("matricola", "")
            self.data_assunzione = raw.get("data_assunzione", self.data_assunzione)
            self.res_ap_ferie = float(raw.get("res_ap_ferie_start", 0.0))
            self.res_ap_par = float(raw.get("res_ap_par_start", 0.0))
            self.includi_patrono = raw.get("includi_patrono", True)

            testo_mail = raw.get("testo_mail_calendario", "")
            self.calendario.aggiorna_da_testo(testo_mail)

            storico_raw = raw.get("storico_assenze", [])
            self.storico_assenze.clear()
            for item in storico_raw:
                self.storico_assenze.append({
                    "data": QDate.fromString(item["data"], config.DATE_FORMAT_INTERNAL),
                    "tipo": item["tipo"],
                    "ore": float(item["ore"])
                })
            return True
        except (OSError, json.JSONDecodeError, ValueError, KeyError):
            return False

    def salva(self, nominativo: str, matricola: str, data_assunzione_str: str, includi_patrono: bool) -> Tuple[
        bool, str]:
        """Salva i dati correnti su file JSON effettuando un backup preventivo."""
        self.nominativo = nominativo
        self.matricola = matricola
        self.data_assunzione = data_assunzione_str
        self.includi_patrono = includi_patrono

        storico_serial = [
            {"data": item["data"].toString(config.DATE_FORMAT_INTERNAL),
             "tipo": item["tipo"], "ore": item["ore"]}
            for item in self.storico_assenze
        ]
        payload = {
            "nominativo": self.nominativo,
            "matricola": self.matricola,
            "data_assunzione": self.data_assunzione,
            "res_ap_ferie_start": self.res_ap_ferie,
            "res_ap_par_start": self.res_ap_par,
            "includi_patrono": self.includi_patrono,
            "storico_assenze": storico_serial,
            "testo_mail_calendario": self.calendario.testo_mail
        }
        try:
            if os.path.exists(config.FILE_DATI):
                shutil.copy2(config.FILE_DATI, config.FILE_BACKUP)
            with open(config.FILE_DATI, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            return True, ""
        except OSError as e:
            return False, str(e)

    def elimina_salvataggi(self) -> bool:
        """Rimuove permanentemente i file di salvataggio e di backup dal disco."""
        try:
            if os.path.exists(config.FILE_DATI):
                os.remove(config.FILE_DATI)
            if os.path.exists(config.FILE_BACKUP):
                os.remove(config.FILE_BACKUP)
            return True
        except OSError:
            return False

    def esporta_csv(self, path: str) -> bool:
        """Esporta lo storico delle assenze in formato CSV delimitato da punto e virgola."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("Data;Tipo;Ore;Info\n")
                for item in self.storico_assenze:
                    is_cal = self.calendario.is_collettivo(item['data'])
                    info = "(Cal)" if is_cal else ""
                    f.write(
                        f"{item['data'].toString(config.DATE_FORMAT_DISPLAY)};"
                        f"{item['tipo']};{item['ore']:.2f};{info}\n"
                    )
            return True
        except OSError:
            return False


class BustaPageParser:
    """Gestisce il parsing intelligente dei cedolini Zucchetti in formato PDF."""

    MESI_ITA = {
        "GENNAIO": 1, "FEBBRAIO": 2, "MARZO": 3, "APRILE": 4,
        "MAGGIO": 5, "GIUGNO": 6, "LUGLIO": 7, "AGOSTO": 8,
        "SETTEMBRE": 9, "OTTOBRE": 10, "NOVEMBRE": 11, "DICEMBRE": 12
    }

    def leggi_testo(self, file_path: str) -> str:
        """Legge ed estrae tutto il testo da un file PDF o TXT."""
        if file_path.lower().endswith(".pdf"):
            if not HAS_PYPDF:
                raise ImportError("Libreria pypdf non installata.")
            reader = PdfReader(file_path)
            return "\n".join(p.extract_text() or "" for p in reader.pages)

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Analizza il testo della busta paga estrapolando i Residui AP
        e lo storico delle singole giornate godute nel mese.
        """
        tc = text.replace('"', '').replace("'", "")
        result: Dict[str, Any] = {
            "ferie": None, "par": None, "mese": None, "anno": None,
            "mese_str": "", "giornate": []
        }

        pat_f = r"FERIE(?:.|\n){0,60}Res\.?AP\s*(-?[\d\.,]+)"
        pat_p = r"P\.?A\.?R\.?(?:.|\n){0,60}Res\.?AP\s*(-?[\d\.,]+)"

        m = re.search(pat_f, tc, re.IGNORECASE)
        if m:
            result["ferie"] = {"res_ap": utils.parse_ore_zucchetti(m.group(1))}

        m = re.search(pat_p, tc, re.IGNORECASE)
        if m:
            result["par"] = {"res_ap": utils.parse_ore_zucchetti(m.group(1))}

        m = re.search(
            r"(GENNAIO|FEBBRAIO|MARZO|APRILE|MAGGIO|GIUGNO|LUGLIO|AGOSTO|"
            r"SETTEMBRE|OTTOBRE|NOVEMBRE|DICEMBRE)\s+(\d{4})",
            tc, re.IGNORECASE
        )
        if m:
            result["mese_str"] = m.group(1).capitalize()
            result["mese"] = self.MESI_ITA.get(m.group(1).upper())
            result["anno"] = int(m.group(2))

            pat_g = r"(\d{2})[A-Z][\s\d,]*?(132|134)[\s,]+(-?\d{1,2},\d{2})"
            for giorno_str, codice, ore_str in re.findall(pat_g, tc):
                try:
                    data_q = QDate(result["anno"], result["mese"], int(giorno_str))  # type: ignore
                    if data_q.isValid():
                        result["giornate"].append({
                            "data": data_q,
                            "tipo": config.TIPO_FERIE if codice == config.CODICE_FERIE_BUSTA else config.TIPO_PAR,
                            "ore": utils.parse_ore_zucchetti(ore_str)
                        })
                except ValueError:
                    continue
        return result


class CalcolatoreLogica:
    """Classe dedicata al calcolo di ratei, spettanze e logiche di scalamento (FIFO)."""

    @staticmethod
    def calcola_mesi_maturati(data_assunzione: date, data_calcolo: date) -> int:
        """Calcola quanti mesi ha maturato il dipendente nell'anno corrente."""
        if data_assunzione > data_calcolo:
            return 0
        mesi_chiusi = data_calcolo.month - 1
        if data_assunzione.year == data_calcolo.year:
            mesi_lavorati = mesi_chiusi - data_assunzione.month + 1
            if data_assunzione.day > 15:
                mesi_lavorati -= 1
            return max(0, mesi_lavorati)
        elif data_assunzione.year < data_calcolo.year:
            return mesi_chiusi
        return 0

    @staticmethod
    def calcola_spettanze(d_ass: date, includi_patrono: bool) -> Tuple[float, float]:
        """Calcola i diritti annui maturabili per Ferie e PAR basandosi sull'anzianità."""
        today = date.today()
        limite_disc = date(2007, 12, 31)
        start_anz = date(2008, 1, 1) if d_ass <= limite_disc else d_ass
        anni_ferie = (today - start_anz).days / 365.25

        spettanza_ferie = 160.0
        if anni_ferie > 18:
            spettanza_ferie += 40.0
        elif anni_ferie > 10:
            spettanza_ferie += 8.0
        if includi_patrono:
            spettanza_ferie += 8.0

        spettanza_par = 104.0
        return spettanza_ferie, spettanza_par

    @staticmethod
    def fifo_avanzato(diritto: float, res_ap: float, maturato: float,
                      goduto_normale: float, goduto_cal: float) -> Dict[str, float]:
        """Esegue il logico scarico delle ore privilegiando il Residuo AP prima del Maturato corrente."""
        maturato_netto = maturato - goduto_cal
        consumo_ap = min(goduto_normale, res_ap)
        res_ap_netto = res_ap - consumo_ap
        consumo_mat_normale = goduto_normale - consumo_ap
        maturato_netto -= consumo_mat_normale
        saldo = res_ap_netto + maturato_netto

        return {
            "diritto": diritto,
            "res_ap": res_ap,
            "maturato": maturato,
            "goduto_tot": goduto_normale + goduto_cal,
            "res_ap_netto": res_ap_netto,
            "saldo": saldo,
        }