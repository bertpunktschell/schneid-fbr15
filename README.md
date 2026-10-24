# Schneid FBR15 Home Assistant Integration

Custom component for controlling a Schneid FBR15 heating controller via the Schneid Connect cloud API (siocs.eu).

## Features

### Sensors (10)
- Raumtemperatur, Außentemperatur, Solltemperatur
- FBR Korrektur, Speicher 1/2 oben
- Status FBR, Firmware, Uhrzeit Regler, Online

### Number (1)
- **FBR Korrektur** — Slider -4 bis +4°C, 0.2°C Schritte

### Select (1)
- **Betriebsmodus** — Anzeige des aktuellen Status

### DateTime (42)
- **Heizzeiten** — Für jeden Wochentag (Mo-So) je 3 Perioden mit Von/Bis
- Jede Zeit einzeln in HA einstellbar

## Installation

1. Kopiere den Ordner `custom_components/schneid_fbr15/` in dein HA `custom_components/` Verzeichnis
2. Starte Home Assistant neu
3. Settings → Devices & Services → Add Integration
4. Suche nach "Schneid FBR15"
5. Schneid Connect Login-Daten eingeben (E-Mail + Passwort)
6. Gerät auswählen

## API Details

Die Integration verbindet sich mit der Schneid Connect Cloud (`api.siocs.eu`):
- **Auth**: Keycloak OAuth2 password grant (`auth.siocs.eu`)
- **Polling**: Alle 60 Sekunden
- **Lesen**: `GET /api/v1/devices/?lhp=api_data_app&query=data_full&device=<id>`
- **Schreiben**: `POST /api/v1/devices/<id>?lhp=api_data_app&setValue=1`
  - Temperaturen: Raw-Wert = Display-Wert / mul
  - Zeiten: Raw-Wert = HHMM als Integer (07:00 = 700, 22:00 = 2200)

## Getestet mit

- Schneid FBR-15 (Firmware 1.1.10) mit MR-12 Controller
- Schneid Connect App v1.4.16
- Device ID: d4b1c36062ec