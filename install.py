# installer Regionalwetter Sachsen-Anhalt
# Copyright 2020 Johanna Roedenbeck
# Distributed under the terms of the GNU Public License (GPLv3)
# derived from Windy

from weecfg.extension import ExtensionInstaller

def loader():
    return RegionalwetterSachsenAnhaltInstaller()

class RegionalwetterSachsenAnhaltInstaller(ExtensionInstaller):
    def __init__(self):
        super(RegionalwetterSachsenAnhaltInstaller, self).__init__(
            version="0.7",
            name='Regionalwetter-Sachsen-Anhalt',
            description='Upload weather data to Regionalwetter Sachsen-Anhalt.',
            author="Johanna Roedenbeck",
            author_email="",
            restful_services='user.regionalwetterSachsenAnhalt.Rwsa',
            config={
                'StdRESTful': {
                    'RegionalwetterSachsenAnhalt': {
                        'enable': 'true',
                        'server_url':"'http://www.regionalwetter-sa.de/daten/get_daten.php'",
                        'station': 'replace_me',
                        'station_model':'replace_me',
                        'username':'replace_me',
                        'location':'replace_me',
                        'zip_code': 'replace_me',
                        'state_code': 'replace_me',
                        'lon_offset':'0',
                        'lat_offset':'0',
                        'skip_upload':'false',
                        'log_url':'false',
                        'T5CM':'None',
                        'daySunD':'None'}}},
            files=[('bin/user', ['bin/user/regionalwetterSachsenAnhalt.py'])]
            )
