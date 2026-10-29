"""
Modulo di configurazione.
Contiene le costanti globali, i percorsi di base dell'applicazione e le info di versione.
"""

import os
import pathlib
import shutil
import sys
import logging

# --- INFO VERSIONE E AGGIORNAMENTI ---
# Legge la versione da version.txt per evitare duplicazione
try:
    with open(os.path.join(os.path.dirname(__file__), "version.txt"), "r") as f:
        APP_VERSION = f.read().strip()
except Exception:
    APP_VERSION = "2.4.0"  # Fallback se version.txt non esiste

# Sostituisci questi due valori con i dati reali del tuo account GitHub
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "enkas79")
GITHUB_REPO = os.getenv("GITHUB_REPO", "GestioneFeriePAR")

GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# --- ICONA APPLICAZIONE ---
# Risolve icon.ico sia in esecuzione da sorgente sia da eseguibile PyInstaller
# (dove non esiste __file__ utilizzabile: le risorse stanno accanto all'exe).
def _get_icon_path() -> str:
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(__file__)
    path = os.path.join(base, "icon.ico")
    return path if os.path.exists(path) else ""


ICON_PATH = _get_icon_path()

# --- PERCORSI E FILE ---
# Percorsi di salvataggio (cartella dati applicativa dell'utente, per piattaforma):
# - Windows: %APPDATA%\FeParManager
# - macOS:   ~/Library/Application Support/FeParManager
# - Linux:   $XDG_DATA_HOME/FeParManager (o ~/.local/share/FeParManager)
def _get_base_dir() -> pathlib.Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return pathlib.Path(base) / "FeParManager"


BASE_DIR = _get_base_dir()
BASE_DIR.mkdir(parents=True, exist_ok=True)

# Migrazione una tantum: le versioni precedenti salvavano sempre in ~/FeParManager
# anche su Linux/macOS. Se la nuova cartella e' vuota ma la vecchia esiste, sposta
# i file per non far perdere i dati agli utenti già esistenti.
_OLD_BASE_DIR = pathlib.Path(os.path.expanduser("~")) / "FeParManager"
if _OLD_BASE_DIR != BASE_DIR and _OLD_BASE_DIR.is_dir():
    for _nome_file in ("dati_ferie_par.json", "dati_ferie_par.bak", "ferie_par.log"):
        _vecchio = _OLD_BASE_DIR / _nome_file
        _nuovo = BASE_DIR / _nome_file
        if _vecchio.exists() and not _nuovo.exists():
            shutil.move(str(_vecchio), str(_nuovo))

FILE_DATI = str(BASE_DIR / "dati_ferie_par.json")
FILE_BACKUP = str(BASE_DIR / "dati_ferie_par.bak")
FILE_LOG = str(BASE_DIR / "ferie_par.log")
MAX_BACKUP_COUNT = 3  # numero di backup rotanti mantenuti (.bak, .bak.1, .bak.2, ...)

# --- REGOLE DI BUSINESS ---
MAX_ORE_GIORNALIERE = 8.0

# Spettanze annue base (ore) e bonus per anzianita'
SPETTANZA_BASE_FERIE = 160.0
SPETTANZA_BASE_PAR = 104.0
BONUS_FERIE_ANZIANITA_10 = 8.0
BONUS_FERIE_ANZIANITA_18 = 40.0
BONUS_PATRONO = 8.0
SOGLIA_ANZIANITA_10 = 10.0
SOGLIA_ANZIANITA_18 = 18.0
# Prima del 2008 l'anzianita' si conta dal 1/1/2008 (limite di discriminante)
DATA_LIMITE_ANZIANITA = (2007, 12, 31)
DATA_PARTENZA_ANZIANITA = (2008, 1, 1)

# Nomi dei mesi in italiano (indice 0 = Gennaio)
MESI_NOMI_IT = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
]
# Mappa mese italiano (minuscolo) -> numero mese
MESI_IT_NUMERO = {nome.lower(): i + 1 for i, nome in enumerate(MESI_NOMI_IT)}

# --- ETICHETTE E CODICI ZUCCHETTI ---
TIPO_FERIE = "FERIE"
TIPO_PAR = "PAR"
CODICE_FERIE_BUSTA = "132"
CODICE_PAR_BUSTA = "134"

# --- FORMATTAZIONE DATE ---
DATE_FORMAT_INTERNAL = "yyyy-MM-dd"
DATE_FORMAT_DISPLAY = "dd/MM/yyyy"

# --- CRITTOGRAFIA ---
# Abilita/disabilita la crittografia (default: abilitata se cryptography è installato)
USE_ENCRYPTION = True

# --- LOGGING ---
# Configurazione logging globale
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(FILE_LOG, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
