import os, re, random, logging, json, time
from datetime import datetime
from pathlib import Path
import anthropic
import google.generativeai as genai

# ... (Aradaki db importları aynı kalacak) ...

log = logging.getLogger(__name__)

# İki AI istemcisini de başlat
try:
    claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
except Exception as _e:
    claude_client = None

try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    gemini_model = genai.GenerativeModel('gemini-1.5-pro')
except Exception as _e:
    gemini_model = None

# ... (Aradaki _get_ataturk_quote, _load_recent_authors vb. fonksiyonlar aynı kalacak) ...


def _select_best_quote(philosopher, akim, konu, quotes_list):
    quotes_text = "\n".join(["  %d. %s" % (i+1, q) for i, q in enumerate(quotes_list)])

    system_instruction = """Sen uzman bir felsefe editörüsün. Sana filozofun GERÇEK sözleri verilecek.
Görev: Listeden konuya EN UYGUN sözü seç, MUTLAKA Türkçeye çevir ve formatla.

KESİN KURALLAR:
1. Listede OLMAYAN söz uydurma. Tırnak işareti kullanma.
2. ACIKLAMA kısmında; sözün felsefi arka planını ve modern insan için taşıdığı anlamı inceleyen EN AZ 3-4 PARAGRAFTAN oluşan, derinlikli bir makale yaz.

Yanıt formatı:
SOZ:
[Söz]
---
YAZAR:
[Yazar]
---
AKIM:
[Akım]
---
HASHTAG:
[#Felsefe vb.]
---
ACIKLAMA:
[En az 3 paragraf felsefi yorum]
---
TWITTER:
[Türkçe söz tırnaksız — Yazar Adı]"""

    prompt_content = f"Dusunur: {philosopher}\nAkim: {akim}\nKonu: {konu}\n\nGERCEK sozler listesi:\n{quotes_text}"

    # 1. Claude'u Dene
    if claude_client:
        try:
            msg = claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=900,
                system=system_instruction,
                messages=[{"role": "user", "content": prompt_content}]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            log.warning("Claude API hatasi: %s. Gemini'ye geciliyor..." % e)

    # 2. Gemini'yi Dene (Claude kredi bitirdiyse)
    if gemini_model:
        try:
            response = gemini_model.generate_content(f"{system_instruction}\n\n{prompt_content}")
            return response.text.strip()
        except Exception as e:
            log.warning("Gemini API hatasi: %s. Fallback'e geciliyor..." % e)

    # 3. İkisi de çökerse Manuel Fallback
    log.warning("Her iki AI de basarisiz, manuel secim yapiliyor.")
    result = _fallback_format(philosopher, akim, quotes_list)
    return result or ""
