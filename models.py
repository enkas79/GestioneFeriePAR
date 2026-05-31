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
import base64
import hashlib
from datetime import date
from typing import Dict, List, Set, Tuple, Any, Optional
from PyQt6.QtCore import QDate

import config
import utils

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# --- CRITTOGRAFIA ---
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    config.logger.warning("Libreria 'cryptography' non installata. I dati verranno salvati in chiaro.")


class EncryptionManager:
    """Gestisce la crittografia e decrittografia dei dati usando AES-256 (Fernet)."""
    
    def __init__(self, password: str = ""):
        """
        Inizializza il gestore di crittografia.
        
        Args:
            password (str): Password utente per derivare la chiave. Se vuota, usa una chiave predefinita.
        """
        self.password = password
        self.key = self._derive_key(password) if password else None
        self.cipher_suite = Fernet(self.key) if self.key else None
    
    def _derive_key(self, password: str) -> bytes:
        """Deriva una chiave Fernet (32-byte URL-safe base64) dalla password."""
        # Usa SHA-256 per derivare una chiave di 32 byte
        digest = hashlib.sha256(password.encode()).digest()
        # Fernet richiede una chiave URL-safe base64-encoded di 32 byte
        return base64.urlsafe_b64encode(digest)
    
    def encrypt(self, data: str) -> bytes:
        """Cifra una stringa JSON."""
        if not self.cipher_suite:
            raise ValueError("Nessuna chiave di crittografia disponibile.")
        return self.cipher_suite.encrypt(data.encode('utf-8'))
    
    def decrypt(self, encrypted_data: bytes) -> str:
        """Decifra dati cifrati."""
        if not self.cipher_suite:
            raise ValueError("Nessuna chiave di crittografia disponibile.")
        return self.cipher_suite.decrypt(encrypted_data).decode('utf-8')
    
    @staticmethod
    def is_encrypted(file_path: str) -> bool:
        """Verifica se un file è cifrato (contiene dati binari)."""
        try:
            with open(file_path, 'rb') as f:
                first_bytes = f.read(4)
                # I file JSON iniziano con '{' o '['
                return not (first_bytes.startswith(b'{') or first_bytes.startswith(b'['))
        except Exception:
            return False


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
            config.logger.info(f"Controllo aggiornamenti da {config.GITHUB_API_URL}")
            # Creiamo la richiesta aggiungendo uno User-Agent (richiesto dalle API GitHub)
            req = urllib.request.Request(config.GITHUB_API_URL, headers={'User-Agent': 'GestioneFeriePAR'})

            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    latest_version = data.get("tag_name", "").strip()

                    if not latest_version:
                        config.logger.warning("Nessun tag di versione trovato nella risposta GitHub.")
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
                        config.logger.info(f"Aggiornamento disponibile: {latest_version}")
                        return True, latest_version, html_url
                    else:
                        config.logger.info("Nessun aggiornamento disponibile.")

        except urllib.error.URLError as e:
            config.logger.warning(f"Errore di rete durante il controllo aggiornamenti: {e}")
        except Exception as e:
            config.logger.error(f"Errore controllo aggiornamenti: {e}", exc_info=True)

        return False, config.APP_VERSION, ""


class CalendarManager:
    """Gestisce l'estrazione intelligente dei giorni collettivi (Cal) dalle mail."""

    def __init__(self) -> None:
        self.testo_mail: str = ""
        self.date_collettive: Set[str] = set()
        # Mappa data ISO -> tipo assenza collettiva (FERIE/PAR).
        # Serve per scalare automaticamente le date del calendario dai saldi,
        # anche quando non sono state inserite manualmente nello storico.
        self.tipi_collettivi: Dict[str, str] = {}

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
        self.tipi_collettivi.clear()

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

            tipo_collettivo = self._tipo_da_linea(linea_lower)

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
                                self._aggiungi_data_collettiva(curr, tipo_collettivo)
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
                                self._aggiungi_data_collettiva(qdate, tipo_collettivo)
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
                        self._aggiungi_data_collettiva(qdate, tipo_collettivo)
                except ValueError:
                    continue

        return len(self.date_collettive)

    def _tipo_da_linea(self, linea_lower: str) -> str:
        """Deduce il tipo assenza dalla riga del calendario aziendale."""
        if re.search(r'\bpar\b', linea_lower):
            return config.TIPO_PAR
        if re.search(r'\bferie\b', linea_lower):
            return config.TIPO_FERIE
        # Default prudente: in assenza di indicazione, mantiene il vecchio comportamento
        # di sola marcatura calendario e usa FERIE come tipo scalabile.
        return config.TIPO_FERIE

    def _aggiungi_data_collettiva(self, qdate: QDate, tipo: str) -> None:
        """Registra una data collettiva con il relativo tipo FERIE/PAR."""
        key = qdate.toString(config.DATE_FORMAT_INTERNAL)
        self.date_collettive.add(key)
        self.tipi_collettivi[key] = tipo

    def is_collettivo(self, qdate: QDate) -> bool:
        """Verifica se una data specifica rientra nei giorni collettivi."""
        return qdate.toString(config.DATE_FORMAT_INTERNAL) in self.date_collettive

    def tipo_collettivo(self, qdate: QDate) -> str:
        """Restituisce il tipo FERIE/PAR associato alla data collettiva."""
        return self.tipi_collettivi.get(qdate.toString(config.DATE_FORMAT_INTERNAL), config.TIPO_FERIE)

    def assenze_collettive_programmate(self) -> List[Dict[str, Any]]:
        """Restituisce le date collettive come assenze virtuali da 8 ore."""
        result: List[Dict[str, Any]] = []
        for key in sorted(self.date_collettive):
            qdate = QDate.fromString(key, config.DATE_FORMAT_INTERNAL)
            if qdate.isValid():
                result.append({
                    "data": qdate,
                    "tipo": self.tipi_collettivi.get(key, config.TIPO_FERIE),
                    "ore": config.MAX_ORE_GIORNALIERE,
                    "origine": "Calendario",
                })
        return result


class DataManager:
    """Gestisce la persistenza dei dati utente su file JSON locale (con crittografia opzionale)."""

    def __init__(self, password: str = "") -> None:
        """
        Inizializza il DataManager.
        
        Args:
            password (str): Password per la crittografia. Se vuota, i dati verranno salvati in chiaro.
        """
        self.calendario = CalendarManager()
        self.nominativo: str = ""
        self.matricola: str = ""
        self.data_assunzione: str = ""
        self.res_ap_ferie: float = 0.0
        self.res_ap_par: float = 0.0
        self.includi_patrono: bool = True
        self.storico_assenze: List[Dict[str, Any]] = []
        self.password = password
        self.encryption_manager = EncryptionManager(password) if HAS_CRYPTOGRAPHY and password else None
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

    def _crea_payload(self) -> Dict[str, Any]:
        """Crea il dizionario JSON completo dei dati correnti."""
        storico_serial = [
            {"data": item["data"].toString(config.DATE_FORMAT_INTERNAL),
             "tipo": item["tipo"], "ore": item["ore"]}
            for item in self.storico_assenze
        ]
        return {
            "versione_app": config.APP_VERSION,
            "nominativo": self.nominativo,
            "matricola": self.matricola,
            "data_assunzione": self.data_assunzione,
            "res_ap_ferie_start": self.res_ap_ferie,
            "res_ap_par_start": self.res_ap_par,
            "includi_patrono": self.includi_patrono,
            "storico_assenze": storico_serial,
            "testo_mail_calendario": self.calendario.testo_mail
        }

    def _applica_payload(self, raw: Dict[str, Any]) -> None:
        """Sostituisce completamente i dati in memoria con quelli letti da un payload JSON."""
        self.reset()
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
            qdate = QDate.fromString(item["data"], config.DATE_FORMAT_INTERNAL)
            if qdate.isValid():
                self.storico_assenze.append({
                    "data": qdate,
                    "tipo": item["tipo"],
                    "ore": float(item["ore"])
                })
        self.storico_assenze.sort(key=lambda x: x["data"])

    def _leggi_payload_da_file(self, path: str) -> Dict[str, Any]:
        """Legge e restituisce un payload JSON da file (con decrittografia se necessario)."""
        try:
            # Verifica se il file è cifrato
            if HAS_CRYPTOGRAPHY and self.encryption_manager and EncryptionManager.is_encrypted(path):
                with open(path, 'rb') as f:
                    encrypted_data = f.read()
                decrypted_data = self.encryption_manager.decrypt(encrypted_data)
                raw = json.loads(decrypted_data)
            else:
                # Prova a leggere come JSON in chiaro
                with open(path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
            
            if not isinstance(raw, dict):
                raise ValueError("Il file non contiene un database valido.")
            return raw
        except json.JSONDecodeError as e:
            config.logger.error(f"Errore decodifica JSON in {path}: {e}")
            raise ValueError(f"File corrotto o non valido: {e}")
        except Exception as e:
            config.logger.error(f"Errore lettura file {path}: {e}")
            raise ValueError(f"Impossibile leggere il file: {e}")

    def _salva_payload_su_file(self, path: str, payload: Dict[str, Any], crea_backup: bool = False) -> None:
        """Scrive un payload JSON su file (con crittografia se disponibile), opzionalmente creando un backup preventivo."""
        try:
            if crea_backup and os.path.exists(path):
                shutil.copy2(path, config.FILE_BACKUP)
            
            # Salva con crittografia se disponibile e password impostata
            if HAS_CRYPTOGRAPHY and self.encryption_manager and self.password:
                json_data = json.dumps(payload, indent=4, ensure_ascii=False)
                encrypted_data = self.encryption_manager.encrypt(json_data)
                with open(path, 'wb') as f:
                    f.write(encrypted_data)
                config.logger.info(f"Dati salvati con crittografia in {path}")
            else:
                # Salva in chiaro (fallback)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=4, ensure_ascii=False)
                if not HAS_CRYPTOGRAPHY:
                    config.logger.warning(f"Dati salvati in chiaro in {path} (cryptography non installato)")
                elif not self.password:
                    config.logger.warning(f"Dati salvati in chiaro in {path} (nessuna password fornita)")
        except Exception as e:
            config.logger.error(f"Errore salvataggio file {path}: {e}")
            raise OSError(f"Impossibile salvare il file: {e}")

    def carica(self) -> bool:
        """Carica i dati utente dal file di salvataggio predefinito."""
        if not os.path.exists(config.FILE_DATI):
            config.logger.info("Nessun file di dati esistente. Verrà creato un nuovo database.")
            return False
        try:
            self._applica_payload(self._leggi_payload_da_file(config.FILE_DATI))
            config.logger.info(f"Dati caricati correttamente da {config.FILE_DATI}")
            return True
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as e:
            config.logger.error(f"Errore caricamento dati da {config.FILE_DATI}: {e}")
            return False

    def carica_da_file(self, path: str) -> Tuple[bool, str]:
        """Carica un database salvato dall'utente e sostituisce completamente i dati correnti."""
        try:
            self._applica_payload(self._leggi_payload_da_file(path))
            return True, ""
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as e:
            return False, str(e)

    def salva(self, nominativo: str, matricola: str, data_assunzione_str: str, includi_patrono: bool) -> Tuple[bool, str]:
        """Salva i dati correnti sul database predefinito effettuando un backup preventivo."""
        self.nominativo = nominativo
        self.matricola = matricola
        self.data_assunzione = data_assunzione_str
        self.includi_patrono = includi_patrono

        try:
            self._salva_payload_su_file(config.FILE_DATI, self._crea_payload(), crea_backup=True)
            config.logger.info(f"Dati salvati correttamente in {config.FILE_DATI}")
            return True, ""
        except OSError as e:
            config.logger.error(f"Errore salvataggio dati: {e}")
            return False, str(e)

    def salva_su_file(self, path: str) -> Tuple[bool, str]:
        """Esporta il database corrente in un file JSON scelto dall'utente."""
        try:
            self._salva_payload_su_file(path, self._crea_payload(), crea_backup=False)
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
        try:
            if file_path.lower().endswith(".pdf"):
                if not HAS_PYPDF:
                    config.logger.error("Libreria pypdf non installata. Impossibile leggere PDF.")
                    raise ImportError("Libreria pypdf non installata.")
                reader = PdfReader(file_path)
                testo = "\n".join(p.extract_text() or "" for p in reader.pages)
                config.logger.info(f"Testo estratto da PDF: {file_path}")
                return testo
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    testo = f.read()
                config.logger.info(f"Testo letto da file TXT: {file_path}")
                return testo
        except Exception as e:
            config.logger.error(f"Errore lettura file {file_path}: {e}")
            raise ValueError(f"Impossibile leggere il file {file_path}: {e}")

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
                      goduto_normale: float, goduto_cal: float,
                      ap_scalato_anno_precedente: float = 0.0,
                      res_ap_iniziale: float | None = None) -> Dict[str, float]:
        """
        Esegue lo scarico delle ore privilegiando il Residuo AP prima del Maturato corrente.

        Nota importante:
        - res_ap è il Residuo AP effettivo da usare nel calcolo, già corretto con eventuali
          assenze dell'anno precedente presenti in calendario/storico.
        - res_ap_iniziale è il valore inserito/importato, usato solo per visualizzazione.
        """
        if res_ap_iniziale is None:
            res_ap_iniziale = res_ap

        maturato_netto = maturato - goduto_cal

        # Se il residuo AP è già negativo dopo lo scarico dell'anno precedente,
        # non deve generare un consumo AP negativo sulle assenze dell'anno corrente.
        res_ap_consumabile = max(res_ap, 0.0)
        consumo_ap = min(goduto_normale, res_ap_consumabile)
        res_ap_netto = res_ap - consumo_ap
        consumo_mat_normale = goduto_normale - consumo_ap
        maturato_netto -= consumo_mat_normale
        saldo = res_ap_netto + maturato_netto

        goduto_totale = goduto_normale + goduto_cal
        presunto_fine_anno = res_ap + diritto - goduto_totale

        return {
            "diritto": diritto,
            "res_ap_iniziale": res_ap_iniziale,
            "ap_scalato_anno_precedente": ap_scalato_anno_precedente,
            "res_ap": res_ap,
            "maturato": maturato,
            "goduto_normale": goduto_normale,
            "goduto_cal": goduto_cal,
            "goduto_tot": goduto_totale,
            "maturato_netto": maturato_netto,
            "res_ap_netto": res_ap_netto,
            "saldo": saldo,
            "presunto_fine_anno": presunto_fine_anno,
        }