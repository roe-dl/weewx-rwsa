wns - weewx extension that sends data to Wetternetz-Sachsen
Copyright 2020 Johanna Roedenbeck
Distributed under the terms of the GNU Public License (GPLv3)

You will need an account at Regionalwetter Sachsen-Anhalt

  http://www.regionalwetter-sa.de

Installation instructions:

1) download

wget -O weewx-rwsa.zip https://github.com/roe-dl/weewx-rwsa/archive/master.zip

2) run the installer

sudo wee_extension --install weewx-rwsa.zip

3) enter parameters in the weewx configuration file

[StdRESTful]
    [[RegionalwetterSachsenAnhalt]]
        enable = true
        server_url = 'http://www.regionalwetter-sa.de/daten/get_daten.php'
        station = replace_me
        station_model = replace_me
        username = replace_me
        api_key = 0
        location = replace_me
        zip_code = replace_me
        state_code = replace_me
        lon_offset = 0
        lat_offset = 0
        skip_upload = false

Strings including spaces need quoting.

German umlauts are encoded using % like within URLs.

4) restart weewx

sudo /etc/init.d/weewx stop
sudo /etc/init.d/weewx start
