
import os
import time
import paho.mqtt.client as mqtt
from calculate import calculate_charging_cost
from logger import logger
import psycopg

MQTT_TOPIC = "teslamate/cars/1/state"
MQTT_CAR_ID = 1
DB_URL = os.getenv("DATABASE_URL")

last_state = None

def get_latest_charging_process_id():
    try:
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM charging_processes
                    WHERE end_date IS NOT NULL
                    ORDER BY end_date DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        logger.exception("❌ Błąd podczas pobierania ostatniego charging_process_id z bazy")
        return None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("✅ Połączono z brokerem MQTT")
        client.subscribe(MQTT_TOPIC)
    else:
        logger.error(f"❌ Błąd połączenia z MQTT (kod {rc})")

def on_message(client, userdata, msg):
    global last_state

    payload = msg.payload.decode()

    if last_state == "charging" and payload != "charging":
        logger.info("⚡️ Wykryto zakończenie ładowania")
        charging_id = get_latest_charging_process_id()
        if charging_id:
            logger.info(f"🔍 Ostatnie charging_process_id: {charging_id}")
            calculate_charging_cost(charging_id)
        else:
            logger.warning("⚠️ Nie znaleziono charging_process_id po zakończeniu ładowania")

    last_state = payload

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    mqtt_host = os.getenv("MQTT_HOST", "mosquitto")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))

    logger.info(f"🔌 Łączenie z MQTT {mqtt_host}:{mqtt_port}")
    client.connect(mqtt_host, mqtt_port, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
