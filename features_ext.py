# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE 1 — RESUME PARSING
# ═══════════════════════════════════════════════════════════════════════════════
import secrets as _secrets

def parse_resume_text(filepath):
    """Extract raw text from PDF/DOC resume using pdfminer."""
    text = ""
    try:
        ext = filepath.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            from pdfminer.high_level import extract_text
            text = extract_text(filepath) or ""
        elif ext in ("doc","docx"):
            try:
                import docx
                doc = docx.Document(filepath)
                text = "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                pass
    except Exception:
        pass
    return text

def parse_experience_years(text):
    """Rough heuristic: look for X years / X+ years patterns."""
    import re
    matches = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)', text, re.IGNORECASE)
    return max((int(m) for m in matches), default=0)

def parse_resume_to_profile(filepath):
    """Return dict of extracted fields."""
    text = parse_resume_text(filepath)
    from app import ai_extract_skills
    skills = ai_extract_skills(text)
    exp_years = parse_experience_years(text)
    # Very basic name/email extraction
    import re
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return {
        "skills": ", ".join(skills),
        "experience_years": exp_years,
        "extracted_email": emails[0] if emails else "",
        "raw_text_snippet": text[:500],
        "skill_count": len(skills),
    }
