# Vision-Based Financial PDF Extraction System

## Overview

This system uses Claude's vision API to extract financial data from Czech accounting PDFs by:
1. Converting PDF pages to PNG images
2. Using Claude to visually recognize column layout
3. Extracting data specifically from the "Běžné období" (current period) column
4. Avoiding confusion with "Minulé období" (previous period) data

## Architecture

```
PDF → PNG (PyMuPDF) → Claude Vision API → Structured JSON → Database
```

### Key Components

```
ingest/
├── extraction/
│   ├── pdf_processor.py       # PDF → PNG conversion
│   └── claude_extractor.py    # Claude vision extraction
├── utils/
│   └── constants.py           # Configuration & field mappings
├── models.py                   # Updated with vision fields
├── views.py                    # Vision-based endpoints
├── urls.py                     # API routes
├── media/
│   └── extracted_tables/      # PNG storage
└── tests/
    └── test_extraction.py     # Test suite
```

## Setup

### 1. Install Dependencies

```bash
cd c:\Users\42077\Desktop\scaleupboard
poetry add anthropic
poetry install
```

### 2. Set Environment Variable

Add to your `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

### 3. Run Migrations

```bash
poetry run python manage.py migrate
```

## Usage

### API Endpoints

#### 1. Upload PDF (HTML Form)
```
POST /ingest/upload/
Content-Type: multipart/form-data

Fields:
- pdf_file: PDF file
```

**Response:** Redirects to dashboard with success/error message

---

#### 2. Upload Multiple PDFs (HTML Form)
```
POST /ingest/upload-many/
Content-Type: multipart/form-data

Fields:
- pdf_files: Multiple PDF files
```

**Response:** HTML page with results

---

#### 3. Upload via API (JSON Response)
```
POST /api/ingest/upload-vision/
Content-Type: multipart/form-data

Fields:
- file: Single PDF file
- files: Multiple PDF files (optional)
```

**Single File Response:**
```json
{
  "success": true,
  "file": "vykaz_2023.pdf",
  "year": 2023,
  "doc_type": "income_statement",
  "status": "Analyzováno (Vision API)",
  "confidence": 0.92,
  "local_image_path": "ingest/media/extracted_tables/uuid.png"
}
```

**Multiple Files Response:**
```json
{
  "results": [
    { "success": true, "file": "file1.pdf", ... },
    { "success": true, "file": "file2.pdf", ... }
  ]
}
```

---

#### 4. Get Documents List
```
GET /api/ingest/documents/?scope=latest
GET /api/ingest/documents/?scope=all
```

**Response:**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "vykaz_2023.pdf",
      "year": 2023,
      "doc_type": "income_statement",
      "analyzed": true,
      "uploaded_at": "2023-12-01T10:00:00Z",
      "last_updated": "2023-12-01T10:01:00Z",
      "scale": "thousands",
      "url": "/media/documents/vykaz_2023.pdf"
    }
  ]
}
```

## Testing

### Run Tests

```bash
poetry run python manage.py test ingest.tests.test_extraction
```

### Test Coverage

- PDF to PNG conversion
- Claude vision API extraction
- JSON response parsing
- Model creation and constraints
- Integration tests

## How It Works

### 1. PDF to PNG Conversion

```python
from ingest.extraction.pdf_processor import PDFProcessor

processor = PDFProcessor(dpi=300)
png_bytes = processor.pdf_to_png("path/to/file.pdf", page_num=0)
local_path = processor.save_png_local(png_bytes)
```

**Features:**
- 300 DPI resolution for clarity
- Supports multi-page PDFs
- Saves PNG locally for debugging/audit
- Uses PyMuPDF (fitz) for fast conversion

### 2. Claude Vision Extraction

```python
from ingest.extraction.claude_extractor import FinancialExtractor

extractor = FinancialExtractor()
result = extractor.extract_from_png(png_bytes)
```

**Claude's Task:**
1. Identify document type (income statement vs balance sheet)
2. Find the "Běžné období" column visually
3. Extract values ONLY from that column
4. Map Czech row names to English field names
5. Return structured JSON with confidence score

**Example Extraction:**
```json
{
  "success": true,
  "doc_type": "income_statement",
  "year": 2023,
  "scale": "thousands",
  "extracted_data": {
    "revenue_products_services": 20037,
    "revenue_goods": 330,
    "cogs_materials": 5000,
    "personnel_wages": 5000,
    "depreciation": 1200,
    "income_tax": 2000
  },
  "confidence": 0.92
}
```

### 3. Field Mappings

#### Income Statement Fields
- `revenue_products_services` - Tržby za prodej vlastních výrobků a služeb
- `revenue_goods` - Tržby za prodej zboží
- `cogs_goods` - Náklady vynaložené na prodané zboží
- `cogs_materials` - Spotřeba materiálu a energie
- `services` - Služby
- `personnel_wages` - Mzdové náklady
- `personnel_insurance` - Náklady na sociální zabezpečení
- `taxes_fees` - Daně a poplatky
- `depreciation` - Odpisy dlouhodobého majetku
- `other_operating_costs` - Ostatní provozní náklady
- `other_operating_revenue` - Ostatní provozní výnosy
- `financial_revenue` - Finanční výnosy
- `financial_costs` - Finanční náklady
- `income_tax` - Daň z příjmů

#### Balance Sheet Fields
- `receivables` - Pohledávky
- `inventory` - Zásoby
- `short_term_liabilities` - Krátkodobé závazky
- `cash` - Peněžní prostředky
- `tangible_assets` - Dlouhodobý hmotný majetek
- `total_assets` - Aktiva celkem
- `equity` - Vlastní kapitál
- `total_liabilities` - Závazky celkem
- `trade_payables` - Závazky z obchodních vztahů
- `short_term_loans` - Krátkodobé bankovní úvěry
- `long_term_loans` - Dlouhodobé bankovní úvěry

## Database Schema

### Updated FinancialStatement Model

```python
class FinancialStatement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.IntegerField()
    income = models.JSONField(null=True, blank=True)
    balance = models.JSONField(null=True, blank=True)
    scale = models.CharField(max_length=20, default="thousands")
    document = models.OneToOneField('Document', on_delete=models.CASCADE)

    # New vision-based extraction fields
    local_image_path = models.CharField(max_length=500, null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
```

## Configuration

### Constants (`ingest/utils/constants.py`)

```python
# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 2048

# PDF Processing
PDF_DPI = 300
MAX_PDF_SIZE = 10 * 1024 * 1024  # 10MB

# Storage
EXTRACTED_TABLES_DIR = "ingest/media/extracted_tables"
```

## Error Handling

The system handles various error scenarios:

1. **Missing API Key**: Returns error if `ANTHROPIC_API_KEY` not set
2. **Invalid PDF**: Returns error if PDF cannot be opened
3. **Invalid JSON Response**: Falls back to error response
4. **Missing Fields**: Sets fields to `null` if not found in PDF
5. **Low Confidence**: Still saves data but includes confidence score

## Debugging

### View Extracted PNG

PNGs are saved to `ingest/media/extracted_tables/` with UUID filenames.
You can view these to verify what Claude saw.

### Check Logs

```python
import logging
logger = logging.getLogger('ingest')
```

Logs include:
- PDF conversion success/failure
- PNG save location
- Claude API request/response
- Extraction confidence scores
- Error details with stack traces

## Performance

- **PDF → PNG**: ~500ms (300 DPI, single page)
- **Claude Vision API**: ~2-4 seconds
- **Total Processing Time**: ~3-5 seconds per document

## Limitations

1. **First Page Only**: Currently extracts from page 0 only
2. **Single Column**: Extracts "Běžné období" only (by design)
3. **No Validation**: Raw extraction without calculated fields
4. **Language**: Optimized for Czech accounting PDFs

## Future Enhancements

- [ ] Multi-page PDF support
- [ ] Batch processing optimization
- [ ] Confidence threshold warnings
- [ ] Manual correction interface
- [ ] Historical data tracking (multiple years)

## Troubleshooting

### Error: "No module named 'anthropic'"

```bash
poetry add anthropic
poetry install
```

### Error: "ANTHROPIC_API_KEY not set"

Add to `.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Error: "No module named 'reportlab'"

Use poetry to run commands:
```bash
poetry run python manage.py makemigrations
poetry run python manage.py migrate
```

### Low Confidence Scores

- Check the PNG in `ingest/media/extracted_tables/`
- Ensure PDF quality is good (not scanned image)
- Verify column headers are clear ("Běžné období")

## Support

For issues or questions, check:
- Vision extraction logs in Django logs
- PNG outputs in `ingest/media/extracted_tables/`
- Test suite: `poetry run python manage.py test ingest.tests`

## License

Part of the ScaleUpBoard financial analysis application.
