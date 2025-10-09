"""
API Routes for Hybrid Parsing
Advanced parsing endpoints with multiple strategies
"""
from pathlib import Path
from typing import Optional
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from app.core.config import settings
from app.parsers import KROSParser, PDFParser, ExcelParser
from app.core.claude_client import ClaudeClient
from app.core.nanonets_client import NanonetsClient
from app.core.mineru_client import MinerUClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/parse", tags=["Parsing"])


# ============================================================================
# HYBRID PARSING ENDPOINTS
# ============================================================================

@router.post("/hybrid")
async def hybrid_parsing(
    file: UploadFile = File(..., description="Document to parse"),
    use_nanonets: bool = Form(default=True, description="Try Nanonets API"),
    use_mineru: bool = Form(default=True, description="Try MinerU (for PDF)"),
    use_claude: bool = Form(default=True, description="Use Claude as fallback"),
    primary_parser: Optional[str] = Form(default=None, description="Primary parser: mineru/nanonets/claude")
):
    """
    Hybrid parsing with multiple strategies
    
    Tries multiple parsing methods and returns the best result:
    1. Try primary parser (if specified)
    2. Try alternative parsers (if enabled)
    3. Combine results if multiple succeed
    
    Args:
        file: Document to parse (XML/PDF/Excel)
        use_nanonets: Whether to try Nanonets
        use_mineru: Whether to try MinerU (PDF only)
        use_claude: Whether to use Claude
        primary_parser: Preferred parser to try first
        
    Returns:
        {
            "success": bool,
            "positions": List[dict],
            "parser_used": str,
            "parsers_attempted": List[str],
            "parsing_details": dict
        }
    """
    try:
        logger.info(f"Hybrid parsing: {file.filename}")
        
        # Save file
        parse_id = str(uuid.uuid4())
        temp_dir = settings.DATA_DIR / "temp" / parse_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = temp_dir / file.filename
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Detect file type
        file_ext = file_path.suffix.lower()
        
        # Initialize clients
        claude = ClaudeClient() if use_claude else None
        nanonets = NanonetsClient() if use_nanonets and settings.NANONETS_API_KEY else None
        mineru = MinerUClient() if use_mineru else None
        
        # Initialize appropriate parser
        results = []
        parsers_attempted = []
        
        # Determine parsing strategy based on file type
        if file_ext == '.xml':
            # KROS XML
            parser = KROSParser(claude_client=claude, nanonets_client=nanonets)
            parsers_attempted.append("kros_parser")
            
            try:
                result = parser.parse(file_path)
                results.append({
                    "parser": "kros_parser",
                    "result": result,
                    "success": True
                })
            except Exception as e:
                logger.warning(f"KROS parser failed: {e}")
                results.append({
                    "parser": "kros_parser",
                    "error": str(e),
                    "success": False
                })
        
        elif file_ext == '.pdf':
            # PDF parsing with multiple strategies
            pdf_parser = PDFParser(claude_client=claude, mineru_client=mineru)
            parsers_attempted.append("pdf_parser")
            
            try:
                result = pdf_parser.parse(file_path)
                results.append({
                    "parser": "pdf_parser",
                    "result": result,
                    "success": True
                })
            except Exception as e:
                logger.warning(f"PDF parser failed: {e}")
                results.append({
                    "parser": "pdf_parser",
                    "error": str(e),
                    "success": False
                })
        
        elif file_ext in ['.xlsx', '.xls']:
            # Excel parsing
            excel_parser = ExcelParser(claude_client=claude)
            parsers_attempted.append("excel_parser")
            
            try:
                result = excel_parser.parse(file_path)
                results.append({
                    "parser": "excel_parser",
                    "result": result,
                    "success": True
                })
            except Exception as e:
                logger.warning(f"Excel parser failed: {e}")
                results.append({
                    "parser": "excel_parser",
                    "error": str(e),
                    "success": False
                })
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}"
            )
        
        # Find best result
        successful_results = [r for r in results if r.get("success")]
        
        if not successful_results:
            # All parsers failed
            return {
                "success": False,
                "error": "All parsers failed",
                "parsers_attempted": parsers_attempted,
                "parsing_details": results
            }
        
        # Use first successful result (or combine multiple)
        best_result = successful_results[0]
        parsed_data = best_result["result"]
        
        # Save parsing results
        import json
        results_path = temp_dir / "parsing_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump({
                "parse_id": parse_id,
                "filename": file.filename,
                "parsed_at": datetime.now().isoformat(),
                "results": results,
                "best_result": parsed_data
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Hybrid parsing successful with {best_result['parser']}")
        
        return {
            "success": True,
            "parse_id": parse_id,
            "positions": parsed_data.get("positions", []),
            "total_positions": parsed_data.get("total_positions", 0),
            "parser_used": best_result["parser"],
            "parsers_attempted": parsers_attempted,
            "document_info": parsed_data.get("document_info", {}),
            "parsing_details": {
                "successful_parsers": len(successful_results),
                "failed_parsers": len(results) - len(successful_results)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hybrid parsing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kros-xml")
async def parse_kros_xml(
    file: UploadFile = File(..., description="KROS XML file")
):
    """
    Parse KROS XML file specifically
    
    Supports:
    - KROS UNIXML (Soupis prací)
    - KROS Table XML (Kalkulace s cenami)
    - Generic KROS formats
    
    Args:
        file: KROS XML file
        
    Returns:
        Parsed positions
    """
    try:
        # Save file
        parse_id = str(uuid.uuid4())
        temp_dir = settings.DATA_DIR / "temp" / parse_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = temp_dir / file.filename
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Parse with KROS parser
        claude = ClaudeClient()
        nanonets = NanonetsClient() if settings.NANONETS_API_KEY else None
        
        parser = KROSParser(claude_client=claude, nanonets_client=nanonets)
        result = parser.parse(file_path)
        
        return {
            "success": True,
            "parse_id": parse_id,
            "positions": result.get("positions", []),
            "total_positions": result.get("total_positions", 0),
            "document_info": result.get("document_info", {}),
            "format": result.get("format", "UNKNOWN")
        }
        
    except Exception as e:
        logger.error(f"KROS XML parsing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats")
async def get_supported_formats():
    """
    Get list of supported file formats and parsers
    
    Returns:
        Information about supported formats and available parsers
    """
    # Check parser availability
    parsers_available = {
        "kros_parser": True,
        "pdf_parser": True,
        "excel_parser": True,
        "nanonets": bool(settings.NANONETS_API_KEY),
        "mineru": False  # Will be checked dynamically
    }
    
    # Check MinerU
    try:
        mineru = MinerUClient()
        parsers_available["mineru"] = mineru.available
    except:
        pass
    
    return {
        "supported_formats": {
            "xml": {
                "extensions": [".xml"],
                "types": ["KROS UNIXML", "KROS Table XML", "Generic XML"],
                "parser": "kros_parser"
            },
            "pdf": {
                "extensions": [".pdf"],
                "types": ["PDF estimates", "Scanned documents"],
                "parsers": ["pdf_parser", "mineru", "nanonets"]
            },
            "excel": {
                "extensions": [".xlsx", ".xls"],
                "types": ["Excel estimates", "Spreadsheets"],
                "parser": "excel_parser"
            }
        },
        "parsers_available": parsers_available,
        "primary_parser": settings.PRIMARY_PARSER,
        "fallback_enabled": settings.FALLBACK_ENABLED
    }
