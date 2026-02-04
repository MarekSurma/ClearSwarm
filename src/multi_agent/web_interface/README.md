# Multi-Agent Web Interface

Web interface dla systemu multi-agent, umożliwiający zarządzanie agentami i monitorowanie ich działania w czasie rzeczywistym.

## Funkcjonalności

### 1. Uruchamianie Agentów
- Formularz do wyboru agenta i wysłania wiadomości
- Wyświetlanie opisu agenta przy wyborze
- Uruchamianie agentów w tle (asynchronicznie)
- Potwierdzenie uruchomienia z wyświetleniem ID agenta

### 2. Monitorowanie Wykonań
- **Root Executions** - tylko agenty główne (bez rodzica)
- **All Executions** - wszystkie wykonania (w tym sub-agenty)
- **Running** - tylko aktualnie działające agenty
- Auto-refresh co 3 sekundy (opcjonalnie)
- Wyświetlanie statusu: running/completed
- Czasy rozpoczęcia i czasy trwania
- Identyfikatory agentów

### 3. Szczegóły Wykonania
- **Execution Tree** - wizualizacja drzewa wywołań agentów i narzędzi
- **Details** - szczegółowe informacje o agencie i jego wywołaniach narzędzi
- **Log** - pobieranie pełnego loga JSON

### 4. Real-time Updates (WebSocket)
- Automatyczne odświeżanie listy wykonań
- Monitoring bieżących stanów agentów
- Wskaźnik połączenia (online/offline)
- Licznik aktywnych agentów
- Auto-reconnect w przypadku utraty połączenia

## Architektura

```
web_interface/
├── app.py                 # Główna aplikacja FastAPI
├── api/
│   ├── agents.py          # Endpoints dla agentów (lista, uruchamianie)
│   ├── executions.py      # Endpoints dla historii wykonań
│   └── websocket.py       # WebSocket dla real-time updates
└── static/
    ├── index.html         # Główna strona HTML
    ├── css/
    │   └── style.css      # Stylowanie (dark theme)
    └── js/
        ├── main.js        # Główna logika aplikacji
        ├── tree.js        # Wizualizacja drzewa wykonań
        └── websocket.js   # WebSocket client

```

## REST API Endpoints

### Agents
- `GET /api/agents` - Lista wszystkich dostępnych agentów
- `GET /api/agents/{name}` - Informacje o konkretnym agencie
- `POST /api/agents/run` - Uruchomienie agenta
  ```json
  {
    "agent_name": "coordinator",
    "message": "Calculate 15 + 27"
  }
  ```
- `GET /api/tools` - Lista wszystkich dostępnych narzędzi

### Executions
- `GET /api/executions` - Wszystkie wykonania agentów
- `GET /api/executions/roots` - Tylko root executions
- `GET /api/executions/{agent_id}` - Szczegóły wykonania
- `GET /api/executions/{agent_id}/tree` - Drzewo wykonania (z dziećmi)
- `GET /api/executions/{agent_id}/log` - Pełny log JSON
- `GET /api/executions/{agent_id}/tools` - Lista wykonanych narzędzi

### WebSocket
- `WS /ws/updates` - Real-time updates o wszystkich wykonaniach
- `WS /ws/agent/{agent_id}` - Monitoring konkretnego agenta

## Uruchomienie

### 1. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 2. Uruchomienie serwera

```bash
# Z głównego katalogu projektu
python -m uvicorn multi_agent.web_interface.app:app --reload

# Lub bezpośrednio
cd src
uvicorn multi_agent.web_interface.app:app --reload --host 0.0.0.0 --port 8000
```

### 3. Dostęp do interfejsu

Otwórz przeglądarkę: [http://localhost:8000](http://localhost:8000)

## Użycie

### Uruchomienie agenta

1. Wybierz agenta z listy rozwijanej
2. Wprowadź wiadomość dla agenta
3. Kliknij "Launch Agent"
4. Agent zostanie uruchomiony w tle
5. Wykonanie pojawi się automatycznie na liście

### Monitorowanie wykonania

1. Wykonania pojawiają się automatycznie na liście
2. Zielony status = completed, Pomarańczowy = running
3. Kliknij "View Tree" aby zobaczyć drzewo wywołań
4. Kliknij "Details" aby zobaczyć szczegóły i wywołania narzędzi
5. Kliknij "Log" aby pobrać pełny log JSON

### Auto-refresh

- Kliknij przycisk "▶️ Auto" aby włączyć auto-refresh
- Lista odświeża się co 3 sekundy
- Kliknij "⏸️ Auto" aby wyłączyć

### Real-time monitoring

- WebSocket połączenie jest aktywne automatycznie
- Wskaźnik "Connected" pokazuje status połączenia
- Licznik "Running: X" pokazuje aktywne agenty
- W przypadku utraty połączenia następuje auto-reconnect

## Technologie

### Backend
- **FastAPI** - framework webowy
- **Uvicorn** - ASGI server
- **WebSockets** - real-time komunikacja
- **SQLite** - baza danych (agents.db)
- **Pydantic** - walidacja danych

### Frontend
- **HTML5** - struktura strony
- **CSS3** - stylowanie (dark theme, responsywne)
- **Vanilla JavaScript** - logika aplikacji (bez frameworków)
- **WebSocket API** - real-time updates
- **Fetch API** - REST API calls

## Integracja z multi-agent

Web interface integruje się z istniejącym systemem poprzez:

1. **Database** - bezpośredni dostęp do `agents.db`
2. **AgentLoader** - używa tego samego loadera co CLI
3. **ToolLoader** - dostęp do wszystkich narzędzi
4. **Logs** - czyta pliki JSON z katalogu `logs/`

## Rozszerzanie

### Dodanie nowego endpointu

1. Utwórz funkcję w odpowiednim pliku w `api/`
2. Dodaj dekorator `@router.get()` lub `@router.post()`
3. Endpoint będzie automatycznie dostępny

### Dodanie nowej funkcjonalności w UI

1. Dodaj HTML w `static/index.html`
2. Dodaj style w `static/css/style.css`
3. Dodaj logikę w `static/js/main.js`

### Własne WebSocket events

1. Modyfikuj `api/websocket.py` aby wysyłać nowe typy wiadomości
2. Obsłuż je w `handleWebSocketMessage()` w `websocket.js`

## Uwagi

- Interface działa równolegle z CLI - oba mogą być używane jednocześnie
- Baza danych SQLite jest współdzielona
- Logi są zapisywane w tym samym katalogu `logs/`
- WebSocket automatycznie reconnectuje się po utracie połączenia
- Auto-refresh można wyłączyć aby zmniejszyć obciążenie

## Troubleshooting

### Port 8000 zajęty
```bash
uvicorn multi_agent.web_interface.app:app --port 8080
```

### Brak połączenia WebSocket
- Sprawdź czy serwer działa
- Sprawdź konsolę przeglądarki (F12)
- WebSocket próbuje reconnect automatycznie

### Nie widać wykonań
- Sprawdź czy baza `agents.db` istnieje
- Uruchom przynajmniej jednego agenta przez CLI
- Kliknij przycisk "Refresh"

### Static files nie ładują się
- Sprawdź czy katalog `static/` istnieje
- Sprawdź ścieżkę w `app.py` (powinna być względna)
