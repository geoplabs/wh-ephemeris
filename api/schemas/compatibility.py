"""Schemas for compatibility analysis."""

from datetime import date as Date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class PlaceInput(BaseModel):
    """Location information for birth chart."""
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    tz: str = Field(..., description="Timezone (e.g., 'Asia/Kolkata')")


class PersonInput(BaseModel):
    """Birth data for a person."""
    name: Optional[str] = Field(None, description="Person's name")
    pronouns: Optional[str] = Field(None, description="Preferred pronouns (e.g., 'he/him', 'she/her', 'they/them')")
    date: Date = Field(..., description="Birth date")
    time: str = Field(..., description="Birth time (HH:MM:SS)")
    place: PlaceInput = Field(..., description="Birth place")


class BasicCompatibilityRequest(BaseModel):
    """Request for basic zodiac sign compatibility (Sun sign only)."""
    person1_sign: str = Field(..., description="Zodiac sign of person 1 (e.g., 'Aries', 'Taurus')")
    person2_sign: str = Field(..., description="Zodiac sign of person 2")
    person1_name: Optional[str] = Field(None, description="Optional name for person 1")
    person2_name: Optional[str] = Field(None, description="Optional name for person 2")
    person1_pronouns: Optional[str] = Field(None, description="Optional pronouns for person 1 (e.g., 'he/him', 'she/her', 'they/them')")
    person2_pronouns: Optional[str] = Field(None, description="Optional pronouns for person 2")
    compatibility_type: Literal["love", "friendship", "business"] = Field(
        "love", 
        description="Type of compatibility to analyze"
    )
    system: Literal["western", "vedic"] = Field("western", description="Astrological system")
    llm: bool = Field(True, description="Use LLM for personalized narratives (true) or engine-only computation (false)")


class AdvancedCompatibilityRequest(BaseModel):
    """Request for advanced natal chart compatibility analysis."""
    person1: PersonInput = Field(..., description="Full birth data for person 1")
    person2: PersonInput = Field(..., description="Full birth data for person 2")
    compatibility_type: Literal["love", "friendship", "business"] = Field(
        "love", 
        description="Type of compatibility to analyze"
    )
    system: Literal["western", "vedic"] = Field("western", description="Astrological system")
    house_system: str = Field("placidus", description="House system to use")
    llm: bool = Field(True, description="Use LLM for personalized narratives (true) or engine-only computation (false)")


class ElementCompatibility(BaseModel):
    """Elemental compatibility details."""
    person1_element: str
    person2_element: str
    compatibility: str  # "high", "medium", "low"
    description: str


class ModalityCompatibility(BaseModel):
    """Modality (quality) compatibility details."""
    person1_modality: str
    person2_modality: str
    compatibility: str  # "high", "medium", "low"
    description: str


class AspectAnalysis(BaseModel):
    """Analysis of a synastry aspect."""
    aspect_type: str  # "conjunction", "trine", "square", etc.
    planet1: str
    planet2: str
    orb: float
    influence: str  # "positive", "negative", "neutral"
    area_affected: str  # "communication", "emotions", "values", etc.
    description: str


class HouseOverlay(BaseModel):
    """Analysis of planet in partner's house."""
    planet: str
    house: int
    description: str
    impact: str  # "positive", "challenging", "neutral"


class CompatibilityScore(BaseModel):
    """Detailed compatibility scoring."""
    overall: float = Field(..., ge=0, le=100, description="Overall compatibility (0-100)")
    emotional: float = Field(..., ge=0, le=100, description="Emotional connection")
    intellectual: float = Field(..., ge=0, le=100, description="Mental compatibility")
    physical: float = Field(..., ge=0, le=100, description="Physical/sexual chemistry")
    values: float = Field(..., ge=0, le=100, description="Shared values and goals")
    communication: float = Field(..., ge=0, le=100, description="Communication style")
    
    def get_rating(self) -> str:
        """Get text rating from overall score."""
        if self.overall >= 80:
            return "Excellent"
        elif self.overall >= 65:
            return "Good"
        elif self.overall >= 50:
            return "Moderate"
        elif self.overall >= 35:
            return "Challenging"
        else:
            return "Difficult"


class BasicCompatibilityResponse(BaseModel):
    """Response for basic zodiac sign compatibility."""
    person1_sign: str
    person2_sign: str
    compatibility_type: str
    system: str
    
    score: CompatibilityScore
    element_analysis: ElementCompatibility
    modality_analysis: ModalityCompatibility
    
    strengths: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    advice: list[str] = Field(default_factory=list)
    
    summary: str
    detailed_analysis: str
    
    generated_at: str


class AdvancedCompatibilityResponse(BaseModel):
    """Response for advanced natal chart compatibility."""
    person1_name: Optional[str]
    person2_name: Optional[str]
    compatibility_type: str
    system: str
    
    score: CompatibilityScore
    
    # Basic sign compatibility
    sun_sign_compatibility: str
    moon_sign_compatibility: str
    venus_sign_compatibility: Optional[str] = None
    mars_sign_compatibility: Optional[str] = None
    
    # Synastry aspects
    major_aspects: list[AspectAnalysis] = Field(default_factory=list)
    
    # House overlays
    house_overlays: list[HouseOverlay] = Field(default_factory=list)
    
    # Element and modality
    element_analysis: ElementCompatibility
    modality_analysis: ModalityCompatibility
    
    # Composite analysis
    strengths: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    advice: list[str] = Field(default_factory=list)
    
    # Relationship dynamics
    relationship_dynamics: str
    long_term_potential: str
    
    summary: str
    detailed_analysis: str
    
    generated_at: str
