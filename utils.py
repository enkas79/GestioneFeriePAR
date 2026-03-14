"""
Modulo di utilità.
Fornisce funzioni per la manipolazione delle stringhe, conversione ore
e calcolo delle festività nazionali italiane.
"""

from PyQt6.QtCore import QDate

def parse_numero_it(s: str) -> float:
    """
    Converte una stringa numerica in formato italiano in un float.

    Args:
        s (str): Stringa numerica (es. '1.234,56' o '12,50').

    Returns:
        float: Valore numerico convertito.
    """
    try:
        s = s.strip()
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except ValueError:
        return 0.0

def hhmm_to_decimal(val: float) -> float:
    """
    Converte formato sessadecimale in decimale puro per i calcoli.

    Args:
        val (float): Valore in formato ore.minuti (es. 3.30).

    Returns:
        float: Valore in formato decimale (es. 3.50).
    """
    sign = -1.0 if val < 0 else 1.0
    abs_val = abs(val)
    h = int(abs_val)
    m = round((abs_val - h) * 100)
    return sign * (h + m / 60.0)

def decimal_to_hhmm(val: float) -> float:
    """
    Converte formato decimale in sessadecimale per l'interfaccia utente.

    Args:
        val (float): Valore in formato decimale (es. 3.50).

    Returns:
        float: Valore in formato ore.minuti (es. 3.30).
    """
    sign = -1.0 if val < 0 else 1.0
    abs_val = abs(val)
    h = int(abs_val)
    m = round((abs_val - h) * 60)
    return sign * (h + m / 100.0)

def parse_ore_zucchetti(s: str) -> float:
    """
    Legge il valore ore dalla busta Zucchetti e lo restituisce decimale.

    Args:
        s (str): Stringa ore estratta dalla busta.

    Returns:
        float: Valore in formato decimale matematico.
    """
    val = parse_numero_it(s)
    return hhmm_to_decimal(val)

def is_giorno_festivo(dq: QDate) -> bool:
    """
    Restituisce True se la data è un sabato, domenica o festività nazionale.

    Args:
        dq (QDate): Data da controllare.

    Returns:
        bool: True se è un giorno festivo, altrimenti False.
    """
    day, month, year = dq.day(), dq.month(), dq.year()
    if dq.dayOfWeek() >= 6:
        return True

    festivita_fisse = [
        (1, 1), (6, 1), (25, 4), (1, 5), (2, 6),
        (15, 8), (1, 11), (8, 12), (25, 12), (26, 12)
    ]
    if (day, month) in festivita_fisse:
        return True

    # Calcolo Pasquetta (Algoritmo di Gauss)
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mp = (h + l - 7 * m + 114) // 31
    dp = ((h + l - 7 * m + 114) % 31) + 1
    return dq == QDate(year, mp, dp).addDays(1)