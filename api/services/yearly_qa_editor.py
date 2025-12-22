"""QA Editor for Yearly Forecast Narratives.

This module applies quality assurance checks and polishing to LLM-generated
yearly forecast content before it's rendered into PDF.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Import QA polish functions from daily forecast system
try:
    from .option_b_cleaner.phrasebank_integration import (
        apply_qa_polish,
        get_qa_metrics,
    )
    QA_AVAILABLE = True
except ImportError:
    QA_AVAILABLE = False
    logger.warning("Phrasebank QA system not available for yearly forecast QA")


def polish_narrative_text(
    text: str,
    area: str = "general",
    *,
    check_cliches: bool = True,
    check_length: bool = True,
    ensure_readable: bool = True,
) -> str:
    """Apply QA polish to narrative text.
    
    Args:
        text: Raw narrative text from LLM
        area: Content area (career, love, health, general)
        check_cliches: Remove clichés
        check_length: Check sentence length
        ensure_readable: Ensure readability (break long sentences)
        
    Returns:
        Polished, publication-ready text
    """
    if not text or not text.strip():
        return text
    
    # Apply phrasebank QA if available
    if QA_AVAILABLE:
        try:
            text = apply_qa_polish(
                text,
                area=area,
                check_cliches=check_cliches,
                check_length=check_length,
            )
        except Exception as e:
            logger.warning(f"QA polish failed: {e}")
    
    # Additional readability improvements
    if ensure_readable:
        text = _improve_readability(text)
    
    # Remove any remaining artifacts
    text = _remove_artifacts(text)
    
    return text.strip()


def _improve_readability(text: str) -> str:
    """Improve text readability.
    
    - Break up run-on sentences
    - Fix awkward phrasing
    - Ensure proper punctuation
    """
    # Fix common LLM artifacts
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'\.\.+', '.', text)  # Fix multiple periods
    text = re.sub(r',\s*,', ',', text)  # Fix doubled commas
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)  # Fix spacing before punctuation
    
    # Ensure sentences end with punctuation
    sentences = text.split('. ')
    fixed_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and not sentence[-1] in '.!?':
            sentence += '.'
        if sentence:
            fixed_sentences.append(sentence)
    
    text = ' '.join(fixed_sentences)
    
    # Capitalize first letter
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    
    return text


def _remove_artifacts(text: str) -> str:
    """Remove LLM artifacts and unwanted patterns."""
    # Remove meta-commentary
    patterns_to_remove = [
        r'\[.*?\]',  # [Note: ...]
        r'\(AI generated\)',
        r'As an AI.*?[.!?]',
        r'Please note.*?[.!?]',
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Remove excessive enthusiasm (multiple exclamation marks)
    text = re.sub(r'!{2,}', '!', text)
    
    return text.strip()


def qa_edit_monthly_section(section: Dict[str, Any]) -> Dict[str, Any]:
    """Apply QA editing to a monthly section.
    
    Args:
        section: MonthlySection dict with narrative content
        
    Returns:
        Edited section with polished narratives
    """
    edited = section.copy()
    
    # Polish main narrative sections
    if 'overview' in edited:
        edited['overview'] = polish_narrative_text(edited['overview'], area='general')
    
    # Core life areas
    if 'career_and_finance' in edited:
        edited['career_and_finance'] = polish_narrative_text(edited['career_and_finance'], area='career')
    
    if 'love_and_romance' in edited:
        edited['love_and_romance'] = polish_narrative_text(edited['love_and_romance'], area='love')
    
    if 'home_and_family' in edited:
        edited['home_and_family'] = polish_narrative_text(edited['home_and_family'], area='family')
    
    if 'health_and_routines' in edited:
        edited['health_and_routines'] = polish_narrative_text(edited['health_and_routines'], area='health')
    
    # Growth areas
    if 'growth_and_learning' in edited:
        edited['growth_and_learning'] = polish_narrative_text(edited['growth_and_learning'], area='education')
    
    if 'inner_work' in edited:
        edited['inner_work'] = polish_narrative_text(edited['inner_work'], area='spiritual')
    
    if 'rituals_and_journal' in edited:
        edited['rituals_and_journal'] = polish_narrative_text(edited['rituals_and_journal'], area='general')
    
    # Polish planner actions (bullet points)
    if 'planner_actions' in edited and edited['planner_actions']:
        edited['planner_actions'] = [
            _polish_bullet_point(action) for action in edited['planner_actions']
        ]
    
    return edited


def _polish_bullet_point(text: str) -> str:
    """Polish a bullet point text.
    
    - Ensure it's concise (< 100 chars)
    - Starts with action verb if possible
    - No trailing punctuation for bullets
    """
    text = text.strip()
    
    # Remove bullet markers if present
    text = re.sub(r'^[•\-\*]\s*', '', text)
    
    # Remove trailing punctuation for bullets
    if text.endswith('.'):
        text = text[:-1]
    
    # Truncate if too long
    if len(text) > 100:
        text = text[:97] + '...'
    
    # Capitalize first letter
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    
    return text


def qa_edit_year_overview(commentary: str) -> str:
    """Apply QA editing to year-at-a-glance commentary.
    
    Args:
        commentary: Year overview text from LLM
        
    Returns:
        Polished year overview
    """
    return polish_narrative_text(commentary, area='general', ensure_readable=True)


def qa_edit_yearly_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Apply comprehensive QA editing to entire yearly report.
    
    This is the main entry point for QA editing.
    
    Args:
        report: YearlyForecastReport dict
        
    Returns:
        Fully edited and polished report
    """
    logger.info("Applying QA editing to yearly forecast report")
    
    edited = report.copy()
    
    # Polish year-at-a-glance commentary
    if 'year_at_glance' in edited and 'commentary' in edited['year_at_glance']:
        edited['year_at_glance']['commentary'] = qa_edit_year_overview(
            edited['year_at_glance']['commentary']
        )
    
    # Polish eclipse guidance
    if 'eclipses_and_lunations' in edited:
        for i, eclipse in enumerate(edited['eclipses_and_lunations']):
            if 'guidance' in eclipse:
                edited['eclipses_and_lunations'][i]['guidance'] = polish_narrative_text(
                    eclipse['guidance'],
                    area='spiritual'
                )
    
    # Polish all monthly sections
    if 'months' in edited:
        edited['months'] = [
            qa_edit_monthly_section(month) for month in edited['months']
        ]
    
    # Log QA metrics
    _log_qa_metrics(edited)
    
    logger.info("QA editing complete")
    return edited


def _log_qa_metrics(report: Dict[str, Any]) -> None:
    """Log quality metrics for monitoring."""
    if not QA_AVAILABLE:
        return
    
    try:
        # Sample one monthly section for metrics
        if report.get('months'):
            sample_month = report['months'][0]
            overview = sample_month.get('overview', '')
            
            if overview:
                metrics = get_qa_metrics(overview)
                logger.info(
                    "yearly_qa_metrics",
                    extra={
                        "avg_sentence_length": metrics.get("avg_sentence_length"),
                        "has_cliches": metrics.get("has_cliches", False),
                        "passes_checks": metrics.get("passes_checks", True),
                    }
                )
    except Exception as e:
        logger.debug(f"Could not log QA metrics: {e}")


__all__ = [
    'qa_edit_yearly_report',
    'qa_edit_monthly_section',
    'qa_edit_year_overview',
    'polish_narrative_text',
]

