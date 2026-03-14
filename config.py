"""
Modulo di configurazione.
Contiene le costanti globali, i percorsi di base dell'applicazione e le info di versione.
"""

import os
import pathlib

# --- INFO VERSIONE E AGGIORNAMENTI ---
APP_VERSION = "2.0.2"

# Sostituisci questi due valori con i dati reali del tuo account GitHub
GITHUB_OWNER = "enkas79"
GITHUB_REPO = "GestioneFeriePAR"

GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# --- PERCORSI E FILE ---
# Percorsi di salvataggio (Appdata locale dell'utente)
BASE_DIR = pathlib.Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "FeParManager"
BASE_DIR.mkdir(parents=True, exist_ok=True)

FILE_DATI = str(BASE_DIR / "dati_ferie_par.json")
FILE_BACKUP = str(BASE_DIR / "dati_ferie_par.bak")

# --- REGOLE DI BUSINESS ---
MAX_ORE_GIORNALIERE = 8.0

# --- ETICHETTE E CODICI ZUCCHETTI ---
TIPO_FERIE = "FERIE"
TIPO_PAR = "PAR"
CODICE_FERIE_BUSTA = "132"
CODICE_PAR_BUSTA = "134"

# --- FORMATTAZIONE DATE ---
DATE_FORMAT_INTERNAL = "yyyy-MM-dd"
DATE_FORMAT_DISPLAY = "dd/MM/yyyy"