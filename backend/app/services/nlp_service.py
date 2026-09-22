import re
import logging
from typing import Dict, List, Any
import spacy

logger = logging.getLogger("investigation.nlp")

# Global cached spaCy model
_nlp_model = None

def get_spacy_model():
    global _nlp_model
    if _nlp_model is None:
        try:
            _nlp_model = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.warning(f"Could not load en_core_web_sm model directly: {e}. Attempting blank English pipeline.")
            _nlp_model = spacy.blank("en")
    return _nlp_model

# Comprehensive Forensic Regex Patterns
REGEX_PATTERNS = {
    "Email Addresses": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', re.IGNORECASE),
    "Phone Numbers": re.compile(r'(?:\+\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b'),
    "IP Addresses": re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
    "URLs": re.compile(r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)'),
    "Cryptocurrency Wallets": re.compile(r'\b(0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b')
}

def extract_entities_from_text(text: str, evidence_name: str) -> Dict[str, Any]:
    """
    Extracts forensic entities from evidence text using spaCy NER and targeted regex.
    Never invents entities; returns only what exists in the input.
    """
    if not text or not text.strip():
        return {
            "all_entities": [],
            "grouped": {
                "Names": [],
                "Dates": [],
                "Phone Numbers": [],
                "Email Addresses": [],
                "IP & System Addresses": [],
                "Organizations": []
            }
        }

    nlp = get_spacy_model()
    # Process text in chunks if very long to prevent memory issues
    max_chunk = 50000
    doc_text = text[:max_chunk]
    doc = nlp(doc_text)

    names = set()
    dates = set()
    orgs = set()
    locations = set()

    for ent in doc.ents:
        cleaned = ent.text.strip()
        if len(cleaned) < 2 or cleaned.isdigit():
            continue
        if ent.label_ == "PERSON":
            # Filter common false positives
            if not any(token in cleaned.lower() for token in ["http", "www", "file", "error", "user"]):
                names.add(cleaned)
        elif ent.label_ == "DATE":
            dates.add(cleaned)
        elif ent.label_ == "ORG":
            orgs.add(cleaned)
        elif ent.label_ in ["GPE", "LOC"]:
            locations.add(cleaned)

    # Regex extraction
    emails = set(REGEX_PATTERNS["Email Addresses"].findall(text))
    
    # Filter phone numbers to avoid purely short digits or IP duplicates
    raw_phones = REGEX_PATTERNS["Phone Numbers"].findall(text)
    phones = set()
    for p in raw_phones:
        digits_only = re.sub(r'\D', '', p)
        if 7 <= len(digits_only) <= 15:
            phones.add(p.strip())

    ips = set(REGEX_PATTERNS["IP Addresses"].findall(text))
    # Exclude common subnet masks
    ips = {ip for ip in ips if ip not in ["255.255.255.0", "0.0.0.0", "255.255.255.255"]}

    urls = set(REGEX_PATTERNS["URLs"].findall(text))

    # Compile structured list
    all_entities = []
    
    for n in sorted(names):
        all_entities.append({"type": "PERSON", "value": n, "source": evidence_name})
    for d in sorted(dates):
        all_entities.append({"type": "DATE", "value": d, "source": evidence_name})
    for e in sorted(emails):
        all_entities.append({"type": "EMAIL", "value": e, "source": evidence_name})
    for p in sorted(phones):
        all_entities.append({"type": "PHONE", "value": p, "source": evidence_name})
    for ip in sorted(ips):
        all_entities.append({"type": "IP_ADDRESS", "value": ip, "source": evidence_name})
    for org in sorted(orgs):
        all_entities.append({"type": "ORG", "value": org, "source": evidence_name})

    return {
        "all_entities": all_entities,
        "grouped": {
            "Names": sorted(list(names)),
            "Dates": sorted(list(dates)),
            "Phone Numbers": sorted(list(phones)),
            "Email Addresses": sorted(list(emails)),
            "IP & System Addresses": sorted(list(ips)),
            "Organizations": sorted(list(orgs))
        }
    }
