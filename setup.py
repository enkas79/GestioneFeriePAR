"""
Setup script per Gestione Ferie/PAR.
Permette l'installazione come pacchetto Python.
"""

from setuptools import setup, find_packages
import os

# Leggi la versione da version.txt
with open("version.txt", "r") as f:
    VERSION = f.read().strip()

# Leggi il contenuto di README.md
with open("README.md", "r", encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

setup(
    name="GestioneFeriePAR",
    version=VERSION,
    author="Enrico Martini",
    author_email="",  # Inserire email se disponibile
    description="Applicazione desktop per la gestione, il calcolo e il monitoraggio dei saldi di Ferie e PAR",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/enkas79/GestioneFeriePAR",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyQt6>=6.0.0",
        "pypdf>=3.0.0",
        "cryptography>=41.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-qt>=4.0.0",
            "pysqlite3-binary>=0.5.0",
        ],
        "sqlite": [
            "pysqlite3-binary>=0.5.0",
        ],
    },
    entry_points={
        "gui_scripts": [
            "gestione-ferie-par = main:main",
        ],
    },
    package_data={
        "": ["version.txt"],
    },
    include_package_data=True,
    project_urls={
        "Bug Reports": "https://github.com/enkas79/GestioneFeriePAR/issues",
        "Source": "https://github.com/enkas79/GestioneFeriePAR",
    },
)
