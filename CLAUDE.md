# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sayhello is a Flask-based web application for bioinformatics tools, specifically focused on ST26 patent sequence listing conversions and siRNA analysis.

## Running the Application

### Prerequisites
- Python 3.14+ with venv
- Redis server (for Celery async tasks)

### Local Development

```bash
# Activate virtual environment
source venv/bin/activate

# Start Redis (macOS)
brew services start redis

# Start Celery worker
celery -A app.celery worker --loglevel=info &

# Start Flask app
python app.py [port]
```

### Using start.sh
```bash
./start.sh
```

## Architecture

### Core Processing Pipeline (ST26 Excel→XML)

1. **Upload**: `app.py` `/upload` route accepts Excel files
2. **Parse**: `parser.py` reads sequences from Excel sheets (`seqdata`, `basicdata`)
3. **Convert**: `st26autonew.py` orchestrates conversion
4. **Generate**: `xml_generator.py` produces ST26-compliant XML
5. **Download**: `app.py` `/download_xml` serves the result

Key modules:
- `app.py` - Flask application with routes and Celery task definitions
- `st26autonew.py` - Main conversion entry point
- `parser.py` - Excel parsing (reads sheets, handles modifications)
- `xml_generator.py` - XML generation with WIPO ST26 DTD compliance
- `sirna_analysis.py` - siRNA sequence matching analysis

### Routes
- `/` - Main page
- `/st26` - ST26 Excel to XML converter
- `/sirna` - siRNA analysis tool
- `/fragment` - Peptide fragmentation
- `/alignment` - Sequence alignment

### Async Task Processing
Celery handles long-running conversions asynchronously:
- Task: `convert_excel_task` in `app.py`
- Broker: Redis at `redis://localhost:6379/0`
- Status polling: `/task_status/<task_id>`

## XML Generation
The `xml_generator.py` produces WIPO ST26 compliant XML with these root attributes:
```python
root = ET.Element("ST26SequenceListing", {
    "originalFreeTextLanguageCode": "en",
    "nonEnglishFreeTextLanguageCode": "",
    "dtdVersion": "V1_3",
    ...
})
```

## Key File Locations
- Templates: `templates/`
- Static files: `static/`
- Uploaded files: `static/uploads/`
- Generated XML: `static/outputs/`
- Logs: `logs/app_YYYYMMDD.log`

## Environment Variables
- `SECRET_KEY` - Flask session secret
- `DEBUG` - Enable debug mode
- `REDIS_PASSWORD` - Redis auth (if configured)
- `PORT` - Server port override
- `HOST` - Server host (default: 0.0.0.0)
