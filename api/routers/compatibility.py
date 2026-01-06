"""Compatibility analysis API endpoints."""

import logging
import traceback
from fastapi import APIRouter, Body, HTTPException

from ..schemas.compatibility import (
    BasicCompatibilityRequest,
    BasicCompatibilityResponse,
    AdvancedCompatibilityRequest,
    AdvancedCompatibilityResponse,
)
from ..services.compatibility_service import (
    analyze_basic_compatibility,
    analyze_advanced_compatibility,
)
from ..services.llm_client import LLMUnavailableError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/compatibility", tags=["compatibility"])


@router.post("/basic", response_model=BasicCompatibilityResponse)
async def basic_compatibility(req: BasicCompatibilityRequest = Body(...)):
    """
    Analyze basic zodiac sign compatibility (Sun sign only).
    
    This endpoint provides:
    - Quick compatibility analysis based on Sun signs
    - Element and modality compatibility
    - AI-powered personalized narratives
    - Compatibility scores (0-100) for different areas
    - Strengths, challenges, and advice
    
    **Supports:**
    - Love compatibility
    - Friendship compatibility
    - Business compatibility
    
    **Input:** Just the Sun signs (e.g., "Aries", "Taurus")
    
    **Response Time:** ~2-5 seconds (includes LLM generation)
    
    **Example:**
    ```json
    {
        "person1_sign": "Leo",
        "person2_sign": "Sagittarius",
        "compatibility_type": "love",
        "system": "western"
    }
    ```
    """
    try:
        return await analyze_basic_compatibility(req)
    except ValueError as exc:
        logger.error(f"INVALID_SIGN: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except LLMUnavailableError as exc:
        logger.error(f"LLM_UNAVAILABLE: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error(f"BASIC_COMPATIBILITY_ERROR: {exc}")
        logger.error(f"TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze basic compatibility: {str(exc)}"
        ) from exc


@router.post("/advanced", response_model=AdvancedCompatibilityResponse)
async def advanced_compatibility(req: AdvancedCompatibilityRequest = Body(...)):
    """
    Analyze advanced natal chart compatibility with full birth data.
    
    This endpoint provides:
    - Comprehensive synastry analysis (chart-to-chart aspects)
    - Sun, Moon, Venus, Mars sign compatibility
    - Major planetary aspects between charts
    - House overlays analysis
    - Element and modality compatibility
    - AI-powered personalized narratives
    - Detailed compatibility scores
    - Relationship dynamics and long-term potential assessment
    
    **Supports:**
    - Love compatibility (romantic relationships)
    - Friendship compatibility (platonic bonds)
    - Business compatibility (professional partnerships)
    
    **Requires:**
    - Full birth data: date, time, and place for both people
    - Works with both Western (Tropical) and Vedic (Sidereal) systems
    
    **Response Time:** ~5-10 seconds (includes ephemeris calculations + LLM generation)
    
    **Example:**
    ```json
    {
        "person1": {
            "name": "Alice",
            "date": "1990-05-15",
            "time": "14:30:00",
            "place": {
                "lat": 28.6139,
                "lon": 77.2090,
                "tz": "Asia/Kolkata"
            }
        },
        "person2": {
            "name": "Bob",
            "date": "1988-11-22",
            "time": "08:15:00",
            "place": {
                "lat": 19.0760,
                "lon": 72.8777,
                "tz": "Asia/Kolkata"
            }
        },
        "compatibility_type": "love",
        "system": "western",
        "house_system": "placidus"
    }
    ```
    
    **Use Cases:**
    - Dating apps with full profile data
    - Professional relationship consulting
    - Pre-marital compatibility assessment
    - Business partnership evaluation
    - Deep friendship analysis
    """
    try:
        return await analyze_advanced_compatibility(req)
    except LLMUnavailableError as exc:
        logger.error(f"LLM_UNAVAILABLE: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error(f"ADVANCED_COMPATIBILITY_ERROR: {exc}")
        logger.error(f"TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze advanced compatibility: {str(exc)}"
        ) from exc
