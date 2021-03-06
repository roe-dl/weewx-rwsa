# rwsa

rwsa - Treiber für WeeWX zur Übertragung der Wetterdaten an das Regionalwetter Sachsen-Anhalt

## Voraussetzungen

Zur Nutzung ist ein Account beim Anbieter "Regionalwetter Sachsen-Anhalt" erforderlich.

  http://www.regionalwetter-sa.de

## Installation

1) Download

```
wget -O weewx-rwsa.zip https://github.com/roe-dl/weewx-rwsa/archive/master.zip
```

2) Aufruf des Installationsprogrammes

```
sudo wee_extension --install weewx-rwsa.zip
```

3) Eingabe der Zugangsdaten in die Konfigurationsdatei

```
[StdRESTful]
    [[RegionalwetterSachsenAnhalt]]
        enable = true
        server_url = 'http://www.regionalwetter-sa.de/daten/get_daten.php'
        station = Stationskennung
        station_model = Wetterstations-Hardware
        username = Benutzername
        api_key = 0
        location = Ortsname
        zip_code = Postleitzahl
        state_code = Abkürzung des Bundeslandes
        lon_offset = 0
        lat_offset = 0
        skip_upload = false
        log_url = false
```

Eintragungen, die Leerzeichen oder Sonderzeichen enthalten, müssen in Anführungszeichen oder Hochkommata eingeschlossen werden. 
Umlaute müssen mit Prozentzeichen übersetzt werden, wie es in Browsereingabezeilen gemacht wird.

4) WeeWX neu starten

```
sudo /etc/init.d/weewx stop
sudo /etc/init.d/weewx start
```

## Konfigurationsoptionen

* station: Stationskennung, wie sie vom Betreiber mitgeteilt worden ist
* station_model: Bezeichnung der Wetterstationstechnik (wird nur übertragen und angzeigt, hat sonst keine Bedeutung)
* username: Benutzername, wie er vom Betreiber mitgeteilt worden ist.
* location: Ortsname, wo die Wetterstation steht
* zip_code: zugehörige Postleitzahl 
* state_code: Abkürzung des Bundeslandes
* lon_offset,lat_offset: im Normalfall 0
* skip_upload: mit "False" kann bewirkt werden, daß der Treiber alles ausführt außer dem eigentlichen Hochladen
* log_url: legt fest, ob die erzeugte URL mit den Meßdaten ins Syslog-Protokoll geschrieben werden soll (`True`) oder nicht (`False`)

## Verweise (Links):

* [Übersicht zu WeeWX auf Deutsch](https://www.woellsdorf-wetter.de/software/weewx.html)
* [WeeWX](http://weewx.com) - [WeeWX Wiki](https://github.com/weewx/weewx/wiki)
* [Belchertown Skin](https://obrienlabs.net/belchertownweather-com-website-theme-for-weewx/) - [Belchertown skin Wiki](https://github.com/poblabs/weewx-belchertown/wiki)
* [Wöllsdorfer Wetter](https://www.woellsdorf-wetter.de)

