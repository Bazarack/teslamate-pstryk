# PstrykMate

PstrykMate to skrypt który automatycznie przypisuje koszt ładowania w bazie danych TeslaMate, korzystając z dynamicznych cen energii elektrycznej dostarczanych przez API Pstryk. Nasłuchuje zakończenia sesji ładowania za pomocą MQTT i oblicza koszt na podstawie godzinowego zużycia energii.

## Funkcje

- ✅ Integracja z bazą danych TeslaMate (PostgreSQL)
- ⚡ Automatyczne wyliczanie kosztu na podstawie danych z tabel `charging_processes` i `charges`
- 💰 Uwzględnia skalę między zużytą a dodaną energią
- 🔄 Obsługa sesji trwających wiele dni
- 🪪 Możliwość konfiguracji identyfikatora strefy domowej (geofence_id)
- 📊 Szczegółowe logowanie

## Czego nie ma

- ❌ Na ten moment obsługiwany jest tylko jeden samochód


---
## Jak skonfigurować mosquitto w TeslaMate do współpracy z PstrykMate

Domyślnie broker MQTT (`mosquitto`) używany przez TeslaMate **nie nasłuchuje połączeń z zewnątrz kontenera**. Aby `PstrykMate` mógł odbierać komunikaty o zakończeniu ładowania, musimy dodać listener na porcie `1883` i zezwolić na anonimowe połączenia.

### 📌 Dlaczego to potrzebne?

TeslaMate publikuje eventy przez MQTT (np. `status`), ale bez jawnego listenera nie będziemy w stanie odczytywać komunikatów wysyłanych przez TeslaMate.

### 🪜 Krok po kroku

#### 1. Wejdź do kontenera z `mosquitto`

Najpierw znajdź nazwę kontenera (jeśli używasz np Raspberry PI to logujesz się na nie po SSH):

```bash
docker ps
```

Szukaj czegoś w stylu `mosquitto`. Gdy ją masz, wejdź do środka:

```bash
docker exec -it mosquitto sh
```

#### 2. Znajdź i edytuj plik `mosquitto.conf`

Plik konfiguracyjny zazwyczaj znajduje się pod ścieżką:

```
/mosquitto/config/mosquitto.conf
```

Edytuj go np. za pomocą `vi`:

```bash
vi /mosquitto/config/mosquitto.conf
```

Jeśli dostępny jest `nano`, możesz użyć go zamiast `vi`.

#### 3. Dodaj na końcu pliku konfiguracji:

```conf
listener 1883
allow_anonymous true
```

#### 4. Zapisz zmiany i wyjdź z edytora.

W `vi`:
- naciśnij `ESC`
- wpisz `:wq` i zatwierdź Enterem

#### 5. Wyjdź z kontenera:

```bash
exit
```

#### 6. Zrestartuj kontener mosquitto:

```bash
docker restart mosquitto
```

#### 7. (Opcjonalnie) sprawdź, czy port działa:

```bash
docker exec -it mosquitto netstat -tuln
```

Powinieneś zobaczyć:

```
tcp        0      0 0.0.0.0:1883            0.0.0.0:*               LISTEN
```

---

Teraz Twój serwis `PstrykMate` będzie mógł połączyć się z `mosquitto` i odbierać eventy MQTT!

---

## Instalacja i uruchomienie

### 📁 1. Sklonuj repozytorium PstrykMate

```bash
git clone https://github.com/Bazarack/teslamate-pstryk.git
cd teslamate-pstryk
```

---

### 📝2. Skonfiguruj dane dostępowe

Utwórz plik `.env`:

```bash
nano .env
```

Wklej zawartość (zmień dane według swojej konfiguracji):

```env
PSTRYK_API_KEY=<TWÓJ_PSTRYK_API_TOKEN>
DATABASE_URL=postgresql://username:password@database_host/database_name
HOME_GEOFENCE_ID=1
```
Pstryk API Key znajdziesz w aplikacji Pstryk w sekcji `Konto -> Klucz API`
Dane do `DATABASE_URL`trzeba uzupełnić na podstawie tego, co zostało uzupełnione w `docker-compose.yaml`  aplikacji TeslaMate. Należy pamiętać, że jeśli np: hasło zawiera znaki specjalne to muszą one zostać przepuszczone przez `urlencode`

Zapisz (`CTRL+O`, Enter, potem `CTRL+X`).

---

### 🚀 5. Uruchom serwis

```bash
docker compose build
docker compose up -d
```

---

### 🧪 6. Sprawdź logi (opcjonalnie)

```bash
cat app/logger.log
```
Plik powinien zawierać coś takiego:

```
2025-01-01 12:00:00 [INFO] 🔌 Łączenie z MQTT mosquitto:1883
2025-01-01 12:00:00 [INFO] ✅ Połączono z brokerem MQTT
```
Jeśli nie zawiera informacji o połączeniu z brokerem, oznacza to, że trzeba się ponownie przyjrzeć konfiguracji `mosquitto` opisanej wyżej

---

## Jak działa przeliczanie

Po zmianie statusu z  `charging` na jakiś inny (co oznacza zakończenie ładowania):

1. Z bazy `charging_processes` pobierane są dane o energii i geofence.
2. Sprawdzane jest, czy ładowanie odbyło się w domu (`HOME_GEOFENCE_ID`).
3. Dane z tabeli `charges` są agregowane godzinowo.
4. Pobierane są ceny z Pstryk API (z dokładnością do godziny).
5. Przeliczany jest koszt i zapisywany do kolumny `cost` w tabeli `charging_processes`.

---

## Wymagania

- Docker + Docker Compose
- TeslaMate
- Klucz API (do pobrania z panelu Pstryk)

---

## Logi

Logi zapisywane są w pliku:
```
app/logger.log
```

---

## Licencja

MIT License.

---


## ❤️ Podoba się projekt?

☕ Projekt udostępniam wszystkim chętnym za darmo i bardzo mnie będzie cieszyć jeśli komuś się przyda. Jeśli byś jednak chciał/chciała [postawić mi kawkę](https://buycoffee.to/bazarack) to będzie mi niezmiernie miło :)

⚡ Nie jesteś jeszcze w Pstryk? Odbierz 50 zł na prąd! Użyj mojego kodu **GPMLY1** w koszyku w aplikacji. Bonus trafi do Twojego Portfela Pstryk po pierwszej opłaconej fakturze!

🚗 Dopiero planujesz zakup Tesli? Skorzystaj z mojego linka polecającego: [https://ts.la/ukasz425098](https://ts.la/ukasz425098) i odbierz doładowanie na 1000km!

---
