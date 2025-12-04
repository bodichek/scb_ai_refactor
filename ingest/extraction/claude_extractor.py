"""
Financial data extraction using Claude Vision API
Uses Claude to visually recognize columns and extract data from "běžné období"
"""
import base64
import json
import logging
from typing import Dict, Any, Optional
import anthropic

logger = logging.getLogger(__name__)


class FinancialExtractor:
    """Extracts financial data from PNG images using Claude vision"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Financial Extractor

        Args:
            api_key: Anthropic API key (if None, uses ANTHROPIC_API_KEY env var)
            model: Claude model to use (default: claude-3-5-sonnet-20241022)
        """
        # Initialize Anthropic client with explicit parameters only
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            # Let Anthropic read from ANTHROPIC_API_KEY env var
            self.client = anthropic.Anthropic()

        self.model = model or "claude-sonnet-4-20250514"
        self.max_tokens = 2048

    def extract_from_png(self, png_bytes: bytes) -> Dict[str, Any]:
        """
        Extract financial data from PNG image

        Args:
            png_bytes: PNG image as bytes

        Returns:
            Dictionary with extracted data:
            {
                "success": bool,
                "doc_type": "income_statement" | "balance_sheet",
                "year": int,
                "scale": "units" | "thousands",
                "extracted_data": {...},
                "confidence": float,
            }

        Raises:
            Exception: If extraction fails
        """
        try:
            # Convert PNG to base64
            png_base64 = base64.standard_b64encode(png_bytes).decode('utf-8')

            # Prompt for Claude
            prompt = self._build_extraction_prompt()

            # Call Claude API with vision
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": png_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )

            # Extract response text
            response_text = message.content[0].text

            # Clean JSON from response
            cleaned_json = self._clean_json_response(response_text)

            # Parse JSON
            result = json.loads(cleaned_json)

            # Add success flag
            if "success" not in result:
                result["success"] = True

            # Post-process: compute aggregated fields and normalize scale
            result = self._post_process_extraction(result)

            logger.info(f"Extracted data: doc_type={result.get('doc_type')}, "
                       f"year={result.get('year')}, confidence={result.get('confidence')}, "
                       f"scale={result.get('scale')}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            return {
                "success": False,
                "error": f"Failed to parse JSON: {str(e)}",
                "raw_response": response_text
            }
        except Exception as e:
            logger.error(f"Failed to extract data: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _post_process_extraction(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process extracted data:
        1. Compute aggregated fields (revenue, cogs, etc.)
        2. Convert scale to thousands if needed
        """
        if not result.get("success"):
            return result

        data = result.get("extracted_data", {})
        scale = result.get("scale", "thousands")

        # 1. Compute aggregated fields
        data = self._compute_aggregates(data)

        # 2. Convert to thousands if in units
        if scale == "units":
            data = self._convert_to_thousands(data)
            result["scale"] = "thousands"

        result["extracted_data"] = data
        return result

    def _compute_aggregates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute aggregated fields from components:
        - revenue = revenue_products_services + revenue_goods
        - cogs = cogs_goods + cogs_materials
        """
        def safe_add(*values):
            """Add values, treating None as 0, return None if all None"""
            non_none = [v for v in values if v is not None]
            return sum(non_none) if non_none else None

        # Compute revenue (products + goods)
        revenue_products = data.get("revenue_products_services")
        revenue_goods = data.get("revenue_goods")
        if revenue_products is not None or revenue_goods is not None:
            data["revenue"] = safe_add(revenue_products, revenue_goods)

        # Compute COGS (goods + materials)
        cogs_goods = data.get("cogs_goods")
        cogs_materials = data.get("cogs_materials")
        if cogs_goods is not None or cogs_materials is not None:
            data["cogs"] = safe_add(cogs_goods, cogs_materials)

        return data

    def _convert_to_thousands(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert all numeric values from units to thousands
        Dashboard expects all values in thousands
        """
        converted = {}
        for key, value in data.items():
            if value is not None and isinstance(value, (int, float)):
                converted[key] = value / 1000.0
            else:
                converted[key] = value

        logger.info("Converted units to thousands")
        return converted

    def _build_extraction_prompt(self) -> str:
        """Build prompt for Claude vision API"""
        return """Podíváš se na obrázek tabulky účetního výkazu (české účetnictví).

**TVŮJ ÚKOL:**

1. **Rozpoznej typ dokumentu**:
   - "income_statement" (Výkaz zisku a ztráty) nebo
   - "balance_sheet" (Rozvaha)

2. **Najdi sloupec "Běžné období"**:
   - Může být označen jako: "Běžné období", "Běžné", rok (např. "2023"), "Netto"
   - POZOR: IGNORUJ sloupec "Minulé období" (nebo "Minulé" nebo starší rok)!

3. **Extrahuj čísla POUZE z "Běžné období" sloupce**:
   - Přečti KAŽDÝ řádek tabulky
   - Vezmi hodnotu POUZE z "Běžné období" sloupce
   - NIKDY nebereš hodnoty z "Minulé období"

4. **Rozpoznej měřítko (scale)**:
   - Pokud je napsáno "v tisících Kč" → scale = "thousands"
   - Pokud jsou čísla bez uvedení měřítka → scale = "units"

5. **Extrahuj POUZE raw hodnoty z PDF**:
   - Pole která NEJSOU v PDF = null (ne 0!)
   - NEPIŠ agregované hodnoty (revenue, cogs, ebit, net_profit)
   - Ty se spočítají automaticky z komponent

**MAPOVÁNÍ ŘÁDKŮ → POLE:**

**Income Statement (Výkaz zisku a ztráty):**
- "Tržby za prodej zboží" → revenue_goods
- "Tržby za prodej vlastních výrobků a služeb" → revenue_products_services
- "Náklady vynaložené na prodané zboží" → cogs_goods
- "Spotřeba materiálu a energie" → cogs_materials
- "Služby" → cogs_services
- "Mzdové náklady" / "Osobní náklady" → personnel_wages
- "Náklady na sociální zabezpečení" / "Zákonné sociální pojištění" → personnel_insurance
- "Daně a poplatky" → taxes_fees
- "Odpisy dlouhodobého majetku" → depreciation
- "Ostatní provozní náklady" → other_operating_costs
- "Ostatní provozní výnosy" → other_operating_revenue
- "Finanční výnosy" / "Výnosové úroky" → financial_revenue
- "Finanční náklady" / "Nákladové úroky" → financial_costs
- "Daň z příjmů" → income_tax

**Balance Sheet (Rozvaha):**
- "Pohledávky" / "Krátkodobé pohledávky" → receivables
- "Zásoby" → inventory
- "Krátkodobé závazky" → short_term_liabilities
- "Peníze" / "Peněžní prostředky" / "Krátkodobý finanční majetek" → cash
- "Dlouhodobý hmotný majetek" / "DHM" → tangible_assets
- "Aktiva celkem" / "Aktiva" → total_assets
- "Vlastní kapitál" → equity
- "Závazky celkem" / "Cizí zdroje" → total_liabilities
- "Závazky z obchodních vztahů" → trade_payables
- "Krátkodobé bankovní úvěry" → short_term_loans
- "Dlouhodobé bankovní úvěry" → long_term_loans

**VRAŤ ČISTÝ JSON (bez markdown, bez komentářů):**

```json
{
  "doc_type": "income_statement" | "balance_sheet",
  "year": 2023,
  "scale": "units" | "thousands",
  "extracted_data": {
    "revenue_products_services": 20037 | null,
    "revenue_goods": 330 | null,
    "cogs_goods": null,
    "cogs_materials": null,
    "cogs_services": null,
    "personnel_wages": null,
    "personnel_insurance": null,
    "taxes_fees": null,
    "depreciation": null,
    "other_operating_costs": null,
    "other_operating_revenue": null,
    "financial_revenue": null,
    "financial_costs": null,
    "income_tax": null,
    "receivables": null,
    "inventory": null,
    "short_term_liabilities": null,
    "cash": null,
    "tangible_assets": null,
    "total_assets": null,
    "equity": null,
    "total_liabilities": null,
    "trade_payables": null,
    "short_term_loans": null,
    "long_term_loans": null
  },
  "confidence": 0.92
}
```

**DŮLEŽITÉ:**
- Confidence = jak si jsi jistý (0.0 - 1.0)
- null = pole není v PDF
- 0 = pole je v PDF a je nula
- NIKDY nepřepisuj "Minulé období" do "Běžné období"!
"""

    def _clean_json_response(self, response_text: str) -> str:
        """
        Clean JSON from Claude response (remove markdown, comments, etc.)

        Args:
            response_text: Raw response from Claude

        Returns:
            Cleaned JSON string
        """
        text = response_text.strip()

        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1]

        # Remove any leading/trailing whitespace
        text = text.strip()

        return text
