# Start met een lichte Python base image
FROM python:3.11-slim

# Zet werkdirectory in de container
WORKDIR /app

# Kopieer alle bestanden van je project naar de container
COPY . .

# Installeer pip-afhankelijkheden (als je requirements.txt hebt)
# (Indien je geen requirements.txt hebt, kun je deze regel verwijderen of zelf toevoegen)
RUN pip install --no-cache-dir -r requirements.txt

# Zorg ervoor dat main.py als entrypoint kan draaien
# Pas dit pad aan als je een ander script wil runnen
CMD ["python", "smurfen_weekly_bot/smurfenbot_v9_stable.py"]
