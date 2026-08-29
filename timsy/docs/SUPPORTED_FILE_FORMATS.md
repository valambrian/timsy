# Supported File Formats

This document lists major file formats that can be supported as inputs for the Timsy application, organized by category.

## Currently Supported

| Format | Extension | Usage |
|--------|-----------|-------|
| SQL Dump (MariaDB) | `.dat` | Bulk data backup and restore for all models |

## Tabular / Spreadsheet Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| CSV | `.csv` | Comma-separated values; widely supported, easy to produce from any spreadsheet application |
| TSV | `.tsv` | Tab-separated values; avoids comma conflicts in text fields |
| Excel (XLSX) | `.xlsx` | Microsoft Excel workbook; supports multiple sheets (one per model) |
| Excel (XLS) | `.xls` | Legacy Excel format; broader compatibility with older tools |
| ODS | `.ods` | OpenDocument Spreadsheet; LibreOffice/OpenOffice native format |

**Use cases:** Importing activity records, daily plan entries, blueprint entries, and reference data (places, importance levels, urgency levels, parent categories).

## Structured Data Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| JSON | `.json` | Lightweight, human-readable; natural fit for Django serialization |
| XML | `.xml` | Verbose but self-describing; supports schema validation |
| YAML | `.yaml` / `.yml` | Human-friendly data serialization; good for configuration and templates |
| TOML | `.toml` | Minimal configuration format; suitable for blueprint definitions |

**Use cases:** Importing/exporting blueprints, application configuration, bulk data transfer between Timsy instances.

## Calendar / Time-Tracking Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| iCalendar | `.ics` | Standard calendar format; can represent daily plans and scheduled activities |
| Toggl CSV | `.csv` | Export format from the Toggl time tracker |
| Clockify CSV | `.csv` | Export format from the Clockify time tracker |
| Jira CSV | `.csv` | Export format from Jira work logs |

**Use cases:** Importing time tracking data from other tools, exporting daily plans to calendar applications.

## Document / Text Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Plain Text | `.txt` | Simple line-based format for activity lists or quick imports |
| Markdown | `.md` | Structured text; could represent daily plans or activity documentation |

**Use cases:** Quick entry of activity lists, documentation of plans and templates.

## Database Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| SQLite | `.sqlite` / `.db` | Self-contained database file; portable and requires no server |
| SQL Dump (MySQL) | `.sql` | Standard SQL dump; compatible with MySQL and MariaDB |
| Django Fixtures | `.json` / `.xml` | Django's native serialization format for model data |

**Use cases:** Full database migration, backup/restore, data transfer between environments.

## Library Requirements

This section details which Python libraries are needed for each format. The project runs on **Python 3.12** with **Django** and **MariaDB**. Libraries are grouped by whether they ship with the Python standard library or require installation via `pip`.

### Formats Requiring No Additional Libraries

These formats are fully supported by Python's standard library and/or Django built-ins.

| Format | Standard Library Module | Notes |
|--------|------------------------|-------|
| CSV | `csv` | Built-in; handles reading, writing, dialect detection, and custom delimiters |
| TSV | `csv` | Same `csv` module with `delimiter='\t'` |
| JSON | `json` | Built-in; Django also provides `django.core.serializers` for fixture-format JSON |
| XML | `xml.etree.ElementTree` | Built-in; Django also provides an XML serializer for fixtures |
| Plain Text | built-in `open()` / `io` | No special library needed |
| SQLite | `sqlite3` | Built-in; can read `.sqlite` / `.db` files directly |
| SQL Dump (MySQL/MariaDB) | built-in `open()` | Parsed as text and executed against the database connection |
| Django Fixtures | `django.core.management` | Built-in Django command `loaddata` handles JSON and XML fixtures natively |
| TOML | `tomllib` | **Included in Python 3.11+**; read-only. For writing TOML, the third-party `tomli-w` library would be needed |

### Formats Requiring Third-Party Libraries

Each entry below describes the library, what it does, its license, and approximate size impact.

---

#### Excel (XLSX) - `openpyxl`

| | |
|---|---|
| **PyPI** | `pip install openpyxl` |
| **Purpose** | Read and write modern Excel files (.xlsx) |
| **License** | MIT |
| **Dependencies** | `et-xmlfile` (lightweight XML writer) |
| **Size** | ~8 MB installed |
| **Notes** | The de facto standard for .xlsx in Python. Supports reading cell values, multiple sheets, and basic formatting. Does not require Excel to be installed. |

---

#### Legacy Excel (XLS) - `xlrd`

| | |
|---|---|
| **PyPI** | `pip install xlrd` |
| **Purpose** | Read legacy Excel files (.xls, pre-2007 format) |
| **License** | BSD |
| **Dependencies** | None |
| **Size** | ~1 MB installed |
| **Notes** | Read-only. Version 2.0+ only supports .xls (not .xlsx). Only needed if importing files from older Excel versions. Consider skipping this if all users have access to modern Excel or LibreOffice (which can save as .xlsx). |

---

#### OpenDocument Spreadsheet (ODS) - `odfpy`

| | |
|---|---|
| **PyPI** | `pip install odfpy` |
| **Purpose** | Read and write OpenDocument format files (.ods, .odt) |
| **License** | Apache 2.0 |
| **Dependencies** | `defusedxml` (safe XML parsing) |
| **Size** | ~2 MB installed |
| **Notes** | Required for LibreOffice/OpenOffice native spreadsheet files. Somewhat less commonly needed since LibreOffice can also export to .xlsx and .csv. |

---

#### YAML - `PyYAML`

| | |
|---|---|
| **PyPI** | `pip install PyYAML` |
| **Purpose** | Parse and emit YAML documents |
| **License** | MIT |
| **Dependencies** | None (optional C extension `libyaml` for performance) |
| **Size** | ~1 MB installed |
| **Notes** | The most widely used YAML library for Python. Always use `yaml.safe_load()` to prevent arbitrary code execution from untrusted input. Django supports YAML fixtures if PyYAML is installed. |

---

#### iCalendar (ICS) - `icalendar`

| | |
|---|---|
| **PyPI** | `pip install icalendar` |
| **Purpose** | Parse and generate iCalendar (.ics) files per RFC 5545 |
| **License** | BSD |
| **Dependencies** | `python-dateutil`, `pytz` (timezone handling) |
| **Size** | ~2 MB installed (including dependencies) |
| **Notes** | Maps well to Timsy's daily plan and activity record models. VEVENT components can represent scheduled activities with start time, duration, and description. |

---

#### Markdown - `markdown` or `markdown-it-py`

| | |
|---|---|
| **PyPI** | `pip install markdown` or `pip install markdown-it-py` |
| **Purpose** | Parse Markdown text into structured data or HTML |
| **License** | BSD / MIT |
| **Dependencies** | Minimal |
| **Size** | ~1 MB installed |
| **Notes** | Only needed if Markdown files require structured parsing (e.g., extracting activity lists from headings and bullet points). If Markdown is only read as plain text, no library is needed. |

---

#### Character Encoding Detection - `chardet`

| | |
|---|---|
| **PyPI** | `pip install chardet` |
| **Purpose** | Detect the character encoding of text files |
| **License** | LGPL |
| **Dependencies** | None |
| **Size** | ~2 MB installed |
| **Notes** | Optional but recommended. Useful when importing files that may not be UTF-8 (e.g., Excel CSV exports from non-English Windows systems often use cp1252 or latin-1). An alternative is `charset-normalizer` (MIT license, ~1 MB), which is already a dependency of `requests` if present. |

---

### Summary Table

| Format | Library | Built-in? | pip install command |
|--------|---------|-----------|---------------------|
| CSV / TSV | `csv` | Yes | — |
| JSON | `json` | Yes | — |
| XML | `xml.etree.ElementTree` | Yes | — |
| TOML (read) | `tomllib` | Yes (3.11+) | — |
| Plain Text | — | Yes | — |
| SQLite | `sqlite3` | Yes | — |
| SQL Dump | — | Yes | — |
| Django Fixtures | `django.core` | Yes (Django) | — |
| Excel (XLSX) | `openpyxl` | No | `pip install openpyxl` |
| Excel (XLS) | `xlrd` | No | `pip install xlrd` |
| ODS | `odfpy` | No | `pip install odfpy` |
| YAML | `PyYAML` | No | `pip install PyYAML` |
| iCalendar | `icalendar` | No | `pip install icalendar` |
| Markdown | `markdown` | No | `pip install markdown` |
| Encoding detection | `chardet` | No | `pip install chardet` |
| TOML (write) | `tomli-w` | No | `pip install tomli-w` |

## Considerations

### Priority Recommendations

1. **CSV** - Lowest implementation effort, highest compatibility with spreadsheet tools; no new dependencies
2. **JSON** - Native Django support via serializers, good for API-driven imports; no new dependencies
3. **iCalendar (.ics)** - Enables integration with calendar applications; requires `icalendar`
4. **Excel (XLSX)** - Familiar to most users, supports multi-sheet imports; requires `openpyxl`
5. **Django Fixtures** - Built-in Django support, no additional libraries needed
6. **YAML** - Human-friendly for blueprint definitions; requires `PyYAML`

### General Requirements

- All file processing must work offline (no external service calls)
- Imported data must pass the same validation rules as form-entered data
- Clear error reporting for malformed or invalid files
- Support for encoding detection (UTF-8 as default, with fallback via `chardet` if installed)
- File size limits to prevent excessive memory usage
- Third-party libraries must be compatible with Python 3.12 and have permissive licenses
