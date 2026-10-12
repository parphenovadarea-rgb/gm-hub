"""Настройки Sphinx для документации Game Master Hub.

Сборка HTML:  py -m sphinx -b html docs docs/_build/html
"""

import os
import sys

# Чтобы autodoc нашёл пакет gm_hub, добавляем корень проекта.
sys.path.insert(0, os.path.abspath(".."))

project = "Game Master Hub"
copyright = "2026, Парфенова Д. Г."
author = "Парфенова Д. Г."
release = "1.0"
language = "ru"

extensions = [
    "sphinx.ext.autodoc",  # документация из docstrings
    "sphinx.ext.napoleon",  # docstrings в стиле Google (Args, Returns, Raises)
    "sphinx.ext.viewcode",  # ссылки на исходный код
]

autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
napoleon_google_docstring = True
napoleon_numpy_docstring = False

templates_path = []
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = "Game Master Hub — документация"
html_show_sourcelink = False
