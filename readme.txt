rwsa - weewx extension that sends data to Regionalwetter Sachsen-Anhalt
Copyright 2020 Johanna Roedenbeck
Distributed under the terms of the GNU Public License (GPLv3)

Deutsche Version: https://github.com/roe-dl/weewx-rwsa/blob/master/readme-de.md

You will need an account at Regionalwetter Sachsen-Anhalt

  http://www.regionalwetter-sa.de

Installation instructions:

1) download

wget -O weewx-rwsa.zip https://github.com/roe-dl/weewx-rwsa/archive/master.zip

2) run the installer

   WeeWX up to version 4.X

   ```
   sudo wee_extension --install weewx-rwsa.zip
   ```

   WeeWX from version 5.0 on and WeeWX packet installation

   ```
   sudo weectl extension install weewx-rwsa.zip
   ```

   WeeWX from version 5.0 on and WeeWX pip installation into an virtual environment

   ```
   source ~/weewx-venv/bin/activate
   weectl extension install weewx-rwsa.zip
   ```
   
3) enter parameters in the weewx configuration file

[StdRESTful]
    [[RegionalwetterSachsenAnhalt]]
        enable = true
        server_url = 'http://www.regionalwetter-sa.de/daten/get_daten.php'
        station = replace_me
        station_model = replace_me
        username = replace_me
        location = replace_me
        zip_code = replace_me
        state_code = replace_me
        lon_offset = 0
        lat_offset = 0
        skip_upload = false
        log_url = false
        T5CM = None

Strings including spaces need quoting.

4) restart weewx

   for SysVinit systems:

   ```
   sudo /etc/init.d/weewx stop
   sudo /etc/init.d/weewx start
   ```

   for systemd systems:

   ```
   sudo systemctl stop weewx
   sudo systemctl start weewx
   ```

Configuration options:

station: station id as received from the provider
station_model: weather hardware name (transmitted only, no further meaning)
username: user name
location: name of the city or village
zip_code: zip code (Postleitzahl) 
state_code: abbreviation of the state location is in
lon_offset,lat_offset: normally 0
skip_upload: all is done except upload; for debugging purposes
log_url: report data, that are or would be uploaded, to syslog
T5CM: observation type to use for 5cm temperature

Note:

'windDir10' is replaced by 'windDir' if 'windDir10' is not provided
by the driver.

'GTS' and 'GTSdate' are available only if 'weewx-GTS' is installed.

