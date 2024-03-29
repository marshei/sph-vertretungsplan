# sph-vertretungsplan
Schulportal Hessen - Vertretungsplan

Idee dieses kleinen Tools ist es periodisch den Vertretungsplan
des Schulportals in Hessen abzufragen. Können die angegebene
Klasse und Fächer gefunden werden, dann wird eine Nachricht
an die konfigurierten Empfänger gesendet.
Die Nachrichten werden dabei nicht mehrfach versendet.

## Einrichtung

### Pushover Dienst

Nach der Registrierung bei [Pushover](https://pushover.net/) wird
ein _User Key_ angezeigt. Nach der Einrichtung einer Anwendung wird
dieser ein _API Token_ zugeordnet.

Ist die entsprechende App auf dem Handy installiert, kann
von der Webseite testweise eine Nachricht verschickt werden.

### Betrieb

Für den Betrieb braucht es eine Möglichkeit, das Python Skript
periodisch auszuführen. Bisher an einer Linux Installation mit
Python 3.x getestet.

#### Quellen bereitstellen 

```
git clone https://github.com/marshei/sph-vertretungsplan.git
cd sph-vertretungsplan
```

#### Python Environment einrichten

```shell
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

Für die spätere Benutzung ein Shell Skript `sph.sh` erstellen:
```shell
#!/usr/bin/env bash

SCRIPT_HOME="$(dirname $(readlink -f $0))"

source "${SCRIPT_HOME}"/venv/bin/activate

"${SCRIPT_HOME}"/sph_vertretung.py --config-file "${SCRIPT_HOME}/config.yml" #--debug

deactivate
```

#### Konfiguration

Die Konfiguration ist im YAML Format vorgehalten und 
relativ selbsterklärend. Siehe [Beispiel](sph.yml)

#### Periodische Ausführung

Mittels crontab
```shell
crontab -e
```
die folgende Zeile einfügen:
```shell
# Vertretungsplan halb-stündlich zwischen 6 und 22 Uhr wochentags prüfen
00,30 6-22 * * MON,TUE,WED,THU,FRI <path>/sph.sh
```

### Ausführung im Container
Für die Ausführung im Container läuft der Python Prozess in einer Schleife und prüft in einem gegebenen Interval, ob das Schulportal kontaktiert werden soll. Dazu wird die von `cron` bekannte Syntax mit Hilfe von `pycron` geprüft.
Folgende Konfiguration steuert das Verhalten:
```yaml
  execution:
    # specify number of minutes between two checks
    interval: 5
    # cron specification for pycron
    cron:
      - "00,30 6-22 * * MON,TUE,WED,THU,FRI"
      - "00,30 18-20 * * SUN"
```
Ein Interval muss mindestens eine Minute betragen.

Für die Ausführung im Container muss das Container Image mit Hilfe des Skripts `build.sh` erstellt werden. Der Container kann dann wie folgt gestartet werden
```shell
podman run -d --name "sph" \
           -v $(pwd)/run:/app/config:Z \
           localhost/marshei/sph:latest --debug
```

Die Handhabung in einer Registry wird hier nicht beschrieben.