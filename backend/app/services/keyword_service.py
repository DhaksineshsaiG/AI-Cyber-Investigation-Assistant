import re
from typing import List, Dict, Any

KEYWORD_TAXONOMY = {
    "Unauthorized Access": {
        "severity": "high",
        "keywords": ["unauthorized", "bypass", "escalation", "root access", "brute force", "backdoor", "remote desktop", "vpn breach", "admin override", "unrecognized login"]
    },
    "Credential Theft": {
        "severity": "high",
        "keywords": ["password", "credentials", "api key", "private key", "secret token", "auth token", "dump", "hash", "mimikatz", "shadow file", "keystroke"]
    },
    "Malware": {
        "severity": "high",
        "keywords": ["trojan", "ransomware", "payload", "c2 server", "botnet", "exploit", "reverse shell", "dropper", "powershell -enc", "beacon"]
    },
    "Phishing": {
        "severity": "medium",
        "keywords": ["phishing", "spoofed", "fake login", "verify account", "urgent action required", "password reset", "invoice attachment", "macro"]
    },
    "Data Exfiltration": {
        "severity": "high",
        "keywords": ["exfiltration", "confidential", "proprietary", "internal only", "off-record", "export data", "external drive", "usb drive", "mega.nz", "dropbox transfer", "we transfer", "zip archive"]
    },
    "Financial Fraud": {
        "severity": "high",
        "keywords": ["fraud", "bribe", "kickback", "offshore", "wire transfer", "unauthorized transaction", "crypto swap", "launder", "escrow", "shell company"]
    },
    "Suspicious Transfer": {
        "severity": "medium",
        "keywords": ["transfer", "vendor list", "customer database", "financial report", "payroll", "source code", "leaked", "confidential document"]
    },
    "Deletion / Log Wiping": {
        "severity": "high",
        "keywords": ["delete", "wipe", "shred", "clean logs", "clear history", "erase", "remove evidence", "rm -rf", "drop table", "truncate"]
    },
    "Confidential Information": {
        "severity": "medium",
        "keywords": ["strictly confidential", "nda", "restricted", "do not share", "privileged", "secret", "classified"]
    },
    "Extortion": {
        "severity": "high",
        "keywords": ["blackmail", "ransom", "extortion", "pay bitcoin", "publish files", "deadline", "leak online"]
    }
}

def detect_suspicious_keywords(text: str, evidence_name: str) -> List[Dict[str, Any]]:
    """
    Scans evidence text against the cyber-investigation taxonomy.
    Extracts match count, category, severity, and context snippets.
    Never invents keywords; matches against actual evidence content.
    """
    if not text:
        return []

    lowered_text = text.lower()
    detected = []

    for category, meta in KEYWORD_TAXONOMY.items():
        severity = meta["severity"]
        for kw in meta["keywords"]:
            # Word boundary regex search
            pattern = re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE)
            matches = list(pattern.finditer(text))
            
            if matches:
                snippets = []
                for m in matches[:3]:  # Capture up to 3 contextual snippets
                    start = max(0, m.start() - 40)
                    end = min(len(text), m.end() + 40)
                    snippet = text[start:end].replace("\n", " ").strip()
                    snippets.append(f"...{snippet}...")

                detected.append({
                    "keyword": kw,
                    "category": category,
                    "severity": severity,
                    "count": len(matches),
                    "snippets": snippets,
                    "source": evidence_name
                })

    # Sort by severity (high first) and count descending
    severity_order = {"high": 0, "medium": 1, "low": 2}
    detected.sort(key=lambda x: (severity_order.get(x["severity"], 3), -x["count"]))
    return detected
