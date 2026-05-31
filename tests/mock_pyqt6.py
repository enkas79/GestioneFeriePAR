"""
Mock per PyQt6 per eseguire test senza dipendenze grafiche.
"""

from unittest.mock import MagicMock
import sys

# Crea mock per PyQt6.QtCore
QtCore = MagicMock()

# Crea mock per QDate
class MockQDate:
    def __init__(self, year, month, day):
        self._year = year
        self._month = month
        self._day = day
        self._day_of_week = (self._year, self._month, self._day)
        
    def year(self):
        return self._year
    
    def month(self):
        return self._month
    
    def day(self):
        return self._day
    
    def toString(self, fmt):
        return f"{self._year:04d}-{self._month:02d}-{self._day:02d}"
    
    def isValid(self):
        return True
    
    def dayOfWeek(self):
        # Calcola dayOfWeek (0=Domenica, 1=Lunedì, ..., 6=Sabato)
        from datetime import date
        d = date(self._year, self._month, self._day)
        return (d.weekday() + 1) % 7
    
    def addDays(self, n):
        from datetime import date, timedelta
        d = date(self._year, self._month, self._day) + timedelta(days=n)
        return MockQDate(d.year, d.month, d.day)
    
    def addYears(self, n):
        from datetime import date
        d = date(self._year + n, self._month, self._day)
        return MockQDate(d.year, d.month, d.day)
    
    def addMonths(self, n):
        from datetime import date
        month = self._month + n
        year = self._year + month // 12
        month = month % 12
        if month == 0:
            month = 12
            year -= 1
        try:
            d = date(year, month, self._day)
        except ValueError:
            # Gestisce casi come 31 febbraio
            d = date(year, month + 1, 1) - timedelta(days=1)
        return MockQDate(d.year, d.month, d.day)
    
    @staticmethod
    def currentDate():
        from datetime import date
        today = date.today()
        return MockQDate(today.year, today.month, today.day)
    
    @staticmethod
    def fromString(s, fmt):
        # Parsing semplice per formato ISO (yyyy-MM-dd)
        if fmt == "yyyy-MM-dd":
            parts = s.split('-')
            return MockQDate(int(parts[0]), int(parts[1]), int(parts[2]))
        return MockQDate(2023, 1, 1)
    
    def __lt__(self, other):
        return (self._year, self._month, self._day) < (other.year(), other.month(), other.day())
    
    def __le__(self, other):
        return (self._year, self._month, self._day) <= (other.year(), other.month(), other.day())
    
    def __eq__(self, other):
        return (self._year, self._month, self._day) == (other.year(), other.month(), other.day())
    
    def __repr__(self):
        return f"MockQDate({self._year}, {self._month}, {self._day})"


# Aggiungi QDate a QtCore
QtCore.QDate = MockQDate

# Mock per Qt.AlignmentFlag
Qt = MagicMock()
Qt.AlignmentFlag = MagicMock()
Qt.AlignmentFlag.AlignCenter = 0
Qt.AlignmentFlag.AlignLeft = 0
Qt.AlignmentFlag.AlignRight = 0

# Mock per QFont e QColor
QtGui = MagicMock()
QtGui.QFont = MagicMock()
QtGui.QColor = MagicMock()

# Mock per QPrinter
QtPrintSupport = MagicMock()
QtPrintSupport.QPrinter = MagicMock()

# Aggiungi i mock a sys.modules
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtCore'] = QtCore
sys.modules['PyQt6.QtGui'] = QtGui
sys.modules['PyQt6.QtPrintSupport'] = QtPrintSupport
sys.modules['PyQt6.QtWidgets'] = MagicMock()

# Funzione per creare QDate
QDate = MockQDate
