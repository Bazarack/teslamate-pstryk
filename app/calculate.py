import os
import psycopg
import httpx
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from logger import logger
from zoneinfo import ZoneInfo

def fetch_pstryk_prices(target_date: datetime):
    api_key = os.getenv('PSTRYK_API_KEY')
    if not api_key:
        logger.error("Brak API keya Pstryka!")
        return []

    base_url = "https://api.pstryk.pl/integrations/pricing/"
    headers = {
        "Authorization": api_key,
        "Accept": "application/json"
    }

    window_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(days=1)

    params = {
        "resolution": "hour",
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat()
    }

    max_retries = 3
    backoff = 2

    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.get(base_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("frames", [])
        except httpx.RequestError as e:
            logger.warning(f"⚠️ Próba {attempt}/{max_retries} nieudana: {e}")
            if attempt == max_retries:
                logger.exception("❌ Błąd przy pobieraniu cen z API Pstryka — poddaję się.")
            else:
                import time
                time.sleep(backoff * attempt)
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ API zwróciło błąd HTTP {e.response.status_code}: {e.response.text}")
            break

    return []

def calculate_charging_cost(charging_process_id: int):
    logger.info(f"🔌 Obliczanie kosztu ładowania dla ID: {charging_process_id}")

    conn = psycopg.connect(os.getenv("DATABASE_URL"), autocommit=True)
    cur = conn.cursor()

    home_geofence_id = int(os.getenv("HOME_GEOFENCE_ID", "1"))

    cur.execute("""
        SELECT geofence_id, charge_energy_used, charge_energy_added
        FROM charging_processes
        WHERE id = %s
    """, (charging_process_id,))
    row = cur.fetchone()

    if not row:
        logger.warning("Nie znaleziono procesu ładowania.")
        return

    geofence_id, used_total, added_total = row

    if geofence_id != home_geofence_id:
        logger.info(f"⛔️ Ładowanie nie odbyło się w domu (geofence_id={geofence_id}), pomijam.")
        return

    if not all([used_total, added_total]) or added_total == 0:
        logger.warning("Brak danych o zużyciu lub dodanej energii — pomijam skalowanie.")
        scale_factor = 1.0
    else:
        scale_factor = float(used_total) / float(added_total)
        logger.info(f"🔍 Mnożnik różnicy między energy added, a used: x{scale_factor:.3f}")

    cur.execute("""
        SELECT date, charge_energy_added
        FROM charges
        WHERE charging_process_id = %s
        ORDER BY date
    """, (charging_process_id,))
    rows = cur.fetchall()

    if not rows:
        logger.warning("Brak danych w tabeli charges.")
        return

    hourly_kwh = defaultdict(float)
    prev_energy = None

    for timestamp, energy in rows:
        if prev_energy is not None and energy is not None:
            delta = max(float(energy) - float(prev_energy), 0)
            hour = timestamp.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            hourly_kwh[hour] += delta * scale_factor
        prev_energy = energy

    # Obsługa sesji trwających wiele dni
    session_start = min(hourly_kwh.keys())
    session_end = max(hourly_kwh.keys()) + timedelta(hours=1)

    days = []
    current_day = session_start.replace(hour=0)
    while current_day < session_end:
        days.append(current_day)
        current_day += timedelta(days=1)

    price_map = {}
    for day in days:
        frames = fetch_pstryk_prices(day)
        for p in frames:
            dt = datetime.fromisoformat(p['start'].replace("Z", "+00:00")).replace(minute=0, second=0, microsecond=0)
            price_map[dt] = p['price_gross']

    total_cost = 0.0

    for hour, kwh in sorted(hourly_kwh.items()):
        price = price_map.get(hour)
        if price is None:
            logger.warning(f"Brak ceny dla godziny {hour}")
            continue
        cost = kwh * price
        total_cost += cost
        hour_local = hour.astimezone(ZoneInfo("Europe/Warsaw"))
        logger.info(f"  {hour_local.strftime('%Y-%m-%d %H:%M')} → {kwh:.3f} kWh × {price:.2f} zł = {cost:.2f} zł")

    logger.info(f"💸 Szacowany koszt całej sesji: {total_cost:.2f} zł")

    try:
        cur.execute("""
            UPDATE charging_processes
            SET cost = %s
            WHERE id = %s
        """, (round(total_cost, 2), charging_process_id))
        logger.info(f"✅ Koszt zapisany do bazy: {round(total_cost, 2)} zł")
    except Exception as e:
        logger.exception("Błąd przy zapisie do bazy")

    cur.close()
    conn.close()

    logger.info("—" * 80)  # 🔚 Separator sesji w logach
