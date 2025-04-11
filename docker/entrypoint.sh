#!/bin/bash
set -e  # Beende das Script sofort, wenn ein Befehl fehlschlägt

# Starte cron im Hintergrund
if command -v cron >/dev/null; then
    cron
else
    echo "Cron is not available!"
    exit 1
fi

# Optional: Füge hier weitere Logging- oder Healthcheck-Befehle hinzu

# Führt den Scheduler-Script oder den per CMD angegebenen Befehl aus und übernimmt das Signal-Handling
exec "$@"

