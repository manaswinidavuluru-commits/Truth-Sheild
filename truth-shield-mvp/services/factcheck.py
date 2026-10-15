"""
Fact-Checking and News Verification Service for Truth Shield MVP.
Integrates with Google Fact Check ClaimSearch API, Wikipedia API,
authoritative cross-referencing, and linguistic sensationalism analysis.
"""
import os
import re
import urllib.parse
import requests

GOOGLE_FACTCHECK_API_KEY = os.environ.get("GOOGLE_FACTCHECK_API_KEY", "").strip()

# Sensationalist / Clickbait indicators
SENSATIONAL_PATTERNS = [
    r"\b(shocking|unbelievable|miracle cure|secret revealed|they don't want you to know)\b",
    r"\b(100% proof|exposed|conspiracy|mind-blowing|you won't believe)\b",
    r"\b(wake up|mainstream media won't tell you|bombshell|urgent alert)\b",
]

def analyze_linguistics(text):
    """
    Analyzes headline/claim for sensationalism, aggressive capitalization,
    and clickbait linguistic markers.
    """
    indicators = []
    text_clean = text.strip()
    
    # Capitalization ratio
    letters = [c for c in text_clean if c.isalpha()]
    caps = [c for c in letters if c.isupper()]
    cap_ratio = len(caps) / len(letters) if letters else 0
    
    if cap_ratio > 0.4 and len(text_clean) > 15:
        indicators.append({
            "type": "Capitalization Anomaly",
            "description": f"Excessive uppercase lettering ({int(cap_ratio * 100)}% of text). Common in sensationalized claims.",
            "severity": "medium"
        })
    
    # Punctuation emphasis
    if text_clean.count("!") >= 2 or "?!" in text_clean or "!?" in text_clean:
        indicators.append({
            "type": "Punctuation Emphasis",
            "description": "Multiple exclamation/question marks detected, characteristic of emotional triggers.",
            "severity": "low"
        })
        
    # Sensationalist keywords
    matched_phrases = []
    for pattern in SENSATIONAL_PATTERNS:
        matches = re.findall(pattern, text_clean, re.IGNORECASE)
        if matches:
            matched_phrases.extend(matches)
            
    if matched_phrases:
        indicators.append({
            "type": "Sensationalist Phrasing",
            "description": f"Detected clickbait terminology: '{', '.join(set(matched_phrases))}'.",
            "severity": "high"
        })
        
    return {
        "sensationalism_detected": len(indicators) > 0,
        "indicators": indicators,
        "capitalization_ratio": round(cap_ratio, 2)
    }

def query_google_factcheck(query):
    """
    Queries Google Fact Check Tools API if an API key is configured.
    """
    if not GOOGLE_FACTCHECK_API_KEY:
        return None
        
    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "query": query,
            "key": GOOGLE_FACTCHECK_API_KEY,
            "languageCode": "en"
        }
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("claims", [])
    except Exception as e:
        print(f"Google FactCheck API query error: {e}")
    return None

def query_wikipedia_context(query):
    """
    Fetches verified encyclopedia context from Wikipedia API to corroborate entities and claims.
    """
    try:
        # Extract prominent keywords (remove common stop words)
        words = [w for w in re.findall(r'\b[A-Za-z0-9_-]+\b', query) if len(w) > 3]
        search_term = " ".join(words[:4]) if words else query
        
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(search_term)}&utf8=&format=json&srlimit=2"
        headers = {"User-Agent": "TruthShieldBot/1.0 (Verification Tool)"}
        resp = requests.get(url, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            search_results = data.get("query", {}).get("search", [])
            if search_results:
                top_match = search_results[0]
                # Strip basic HTML tags
                snippet = re.sub(r'<[^>]+>', '', top_match.get("snippet", ""))
                title = top_match.get("title", "")
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                return {
                    "source": "Wikipedia Verified Knowledge Base",
                    "title": title,
                    "snippet": snippet,
                    "url": page_url
                }
    except Exception as e:
        print(f"Wikipedia search error: {e}")
    return None

def query_duckduckgo_instant(query):
    """
    Fetches Instant Answer information from DuckDuckGo API.
    """
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "0"
        }
        headers = {"User-Agent": "TruthShieldBot/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        if resp.status_code == 200 and "application/json" in resp.headers.get("Content-Type", ""):
            data = resp.json()
            abstract = data.get("AbstractText", "")
            source = data.get("AbstractSource", "")
            source_url = data.get("AbstractURL", "")
            
            if abstract and source_url:
                return {
                    "source": f"DuckDuckGo Knowledge ({source})" if source else "Authoritative Knowledge Base",
                    "title": data.get("Heading", "Factual Context"),
                    "snippet": abstract,
                    "url": source_url
                }
    except Exception:
        # Graceful fallback when network or upstream instant answer is unavailable
        pass
    return None

def verify_news_claim(claim_text, source_link=None):
    """
    Main verification pipeline for news headlines and claims.
    Adheres strictly to the rule:
    - Never invent evidence.
    - If evidence is insufficient, return 'Unable to Verify'.
    - Return verified source links, ratings, and methodological limitations.
    """
    claim_clean = claim_text.strip()
    evidence_list = []
    
    # 1. Linguistic and stylistic analysis
    ling_analysis = analyze_linguistics(claim_clean)
    if ling_analysis["sensationalism_detected"]:
        for ind in ling_analysis["indicators"]:
            evidence_list.append({
                "type": "Linguistic & Tone Analysis",
                "publisher": "Truth Shield Heuristics",
                "finding": f"{ind['type']}: {ind['description']}",
                "url": None,
                "rating": "Sensationalist Marker",
                "reliability": "Heuristic"
            })
            
    # 2. Check Google Fact Check Tools API if enabled
    claims_from_api = query_google_factcheck(claim_clean)
    found_fact_check = False
    verdict = "Unable to verify"
    verdict_category = "unverified"
    confidence_score = 30
    summary = ""
    
    if claims_from_api:
        for claim_item in claims_from_api[:3]:
            claim_reviews = claim_item.get("claimReview", [])
            for review in claim_reviews:
                found_fact_check = True
                publisher_info = review.get("publisher", {})
                pub_name = publisher_info.get("name", "Independent Fact-Checker")
                pub_site = publisher_info.get("site", "")
                textual_rating = review.get("textualRating", "Reviewed")
                review_url = review.get("url", "")
                title = review.get("title") or claim_item.get("text", "Fact Check Review")
                
                evidence_list.append({
                    "type": "Third-Party Fact Check",
                    "publisher": pub_name,
                    "finding": f"Review of claim: '{claim_item.get('text', '')}' -> Rated as: {textual_rating}",
                    "url": review_url or pub_site,
                    "rating": textual_rating,
                    "reliability": "High (IFCN Signatory)"
                })
                
                # Determine overall verdict from official ratings
                rating_lower = textual_rating.lower()
                if any(w in rating_lower for w in ["false", "pants on fire", "fake", "hoax", "incorrect", "debunked", "misleading"]):
                    verdict = "Debunked / Misleading"
                    verdict_category = "fake"
                    confidence_score = 92
                    summary = f"This claim has been investigated and rated '{textual_rating}' by accredited fact-checkers ({pub_name})."
                elif any(w in rating_lower for w in ["true", "correct", "accurate", "verified"]):
                    verdict = "Verified Authentic"
                    verdict_category = "authentic"
                    confidence_score = 90
                    summary = f"This claim has been investigated and confirmed accurate by {pub_name}."
                elif any(w in rating_lower for w in ["unproven", "inconclusive", "mixture", "half true", "unsupported"]):
                    verdict = "Unproven / Mixed"
                    verdict_category = "suspicious"
                    confidence_score = 65
                    summary = f"Fact-checkers at {pub_name} examined this claim and found it to be '{textual_rating}' or lacking solid proof."

    # 3. If no direct fact-check found, cross-reference Wikipedia & Knowledge Bases
    wiki_context = query_wikipedia_context(claim_clean)
    if wiki_context:
        evidence_list.append({
            "type": "Encyclopedia Context",
            "publisher": wiki_context["source"],
            "finding": f"Context on '{wiki_context['title']}': {wiki_context['snippet']}...",
            "url": wiki_context["url"],
            "rating": "Verified Entity Context",
            "reliability": "Educational / Historical"
        })

    ddg_context = query_duckduckgo_instant(claim_clean)
    if ddg_context:
        evidence_list.append({
            "type": "Knowledge Graph Match",
            "publisher": ddg_context["source"],
            "finding": f"{ddg_context['title']}: {ddg_context['snippet']}",
            "url": ddg_context["url"],
            "rating": "Authoritative Reference",
            "reliability": "General Reference"
        })

    # 4. If source link provided, validate source
    if source_link:
        parsed = urllib.parse.urlparse(source_link)
        domain = parsed.netloc.lower()
        evidence_list.append({
            "type": "User Submitted Source",
            "publisher": domain or "Source Link",
            "finding": f"Origin link provided: {source_link}",
            "url": source_link,
            "rating": "Submitted Source",
            "reliability": "Unverified Link"
        })

    # 5. Formulate final verdict and limitations
    if not found_fact_check:
        verdict = "Unable to verify"
        verdict_category = "unverified"
        confidence_score = 25
        
        if wiki_context or ddg_context:
            summary = "Contextual information was retrieved from open knowledge bases, but no dedicated fact-checking consensus or debunking reports were found specifically addressing this exact claim."
        else:
            summary = "No matching records found across fact-checking databases or reference registries. There is insufficient credible documentation to confirm or refute this claim."

    # Explicit limitations statement
    limitations = (
        "Fact-checking algorithms cannot replace dedicated journalistic field investigation. "
        "Truth Shield cross-references international fact-checking repositories (IFCN), encyclopedic records, "
        "and linguistic heuristics. If a breaking event has occurred very recently, official debunking "
        "or verification articles may not yet have been indexed."
    )

    return {
        "claim": claim_clean,
        "verdict": verdict,
        "verdict_category": verdict_category,
        "confidence_score": confidence_score,
        "summary": summary,
        "evidence": evidence_list,
        "limitations": limitations,
        "has_direct_factcheck": found_fact_check
    }
