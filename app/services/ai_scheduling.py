"""Optional OpenAI-compatible AI provider; NEVER trust returned suggestions.

Set SCHEDULING_AI_ENDPOINT (full chat-completions URL), SCHEDULING_AI_MODEL,
SCHEDULING_AI_API_KEY. If unset, the UI uses deterministic valid suggestions.
"""
import json
import os
from urllib.request import Request, urlopen
from app.services.rescheduling import available_slots, build_prompt, saring_saran
from app.services.scheduling_service import snapshot
from app.models.scheduling import Jadwal

class AIUnavailable(RuntimeError):
    pass

def ai_suggestions(db, schedule_id):
    endpoint = os.environ.get("SCHEDULING_AI_ENDPOINT")
    model = os.environ.get("SCHEDULING_AI_MODEL")
    key = os.environ.get("SCHEDULING_AI_API_KEY")
    if not (endpoint and model and key and endpoint.startswith("https://")):
        raise AIUnavailable("AI belum dikonfigurasi; gunakan saran deterministik")
    jadwal = db.get(Jadwal, schedule_id)
    if jadwal is None:
        return []
    slots = available_slots(db, schedule_id)
    prompt = build_prompt(snapshot(jadwal), slots)
    request = Request(endpoint, data=json.dumps({"model": model, "messages": [
        {"role": "system", "content": "Return only JSON array of schedule suggestions."},
        {"role": "user", "content": prompt}], "temperature": 0.2}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=12) as response:
            body = json.load(response)
        raw = body["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.strip('`').removeprefix('json').strip()
        suggestions = json.loads(raw)
        if not isinstance(suggestions, list):
            raise ValueError("AI tidak mengembalikan array")
        return saring_saran(db, schedule_id, suggestions)
    except Exception as exc:
        raise AIUnavailable("Penyedia AI tidak tersedia atau hasil tidak valid") from exc
