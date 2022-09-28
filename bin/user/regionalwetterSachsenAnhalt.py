# Copyright 2020,2021 Johanna Roedenbeck
# derived from Windy driver by Matthew Wall
# thanks to Gary and Tom Keffer from Weewx development group

"""
This is a weewx extension that uploads data to a RWSA

http://regionalwetter-sa.de/

Minimal configuration

[StdRESTful]
    [[RegionalwetterSachsenAnhalt]]
        enable = true
        server_url = replace_me
        station = station ID
        station_url = replace_me
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

"""

# deal with differences between python 2 and python 3
try:
    # Python 3
    import queue
except ImportError:
    # Python 2
    # noinspection PyUnresolvedReferences
    import Queue as queue

try:
    # Python 3
    from urllib.parse import urlencode
except ImportError:
    # Python 2
    # noinspection PyUnresolvedReferences
    from urllib import urlencode

from distutils.version import StrictVersion
import json
import sys
import time

import six
from six.moves import urllib
from urllib.parse import quote

import weedb
import weewx
import weewx.manager
import weewx.restx
import weewx.units
from weeutil.weeutil import to_bool, to_int, to_float
import weewx.xtypes
from weeutil.weeutil import TimeSpan

VERSION = "0.6.1"

REQUIRED_WEEWX = "3.8.0"
if StrictVersion(weewx.__version__) < StrictVersion(REQUIRED_WEEWX):
    raise weewx.UnsupportedFeature("weewx %s or greater is required, found %s"
                                   % (REQUIRED_WEEWX, weewx.__version__))

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    #log = logging.getLogger(__name__)
    log = logging.getLogger('user.Rwsa')

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'rwsa: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)


class Rwsa(weewx.restx.StdRESTful):
    DEFAULT_URL = 'http://www.regionalwetter-sa.de/daten/get_daten.php'

    def __init__(self, engine, cfg_dict):
        super(Rwsa, self).__init__(engine, cfg_dict)
        loginf("version is %s" % VERSION)
        site_dict = weewx.restx.get_site_dict(cfg_dict, 'RegionalwetterSachsenAnhalt', 'station', 'username', 'state_code', 'zip_code')
        if site_dict is None:
            return

        try:
            site_dict['manager_dict'] = weewx.manager.get_manager_dict_from_config(cfg_dict, 'wx_binding')
        except weewx.UnknownBinding:
            pass
        
        try:
            # set the value if it not already exists, only
            site_dict.setdefault('location',engine.stn_info.location)
            site_dict.setdefault('station_model',engine.stn_info.hardware)
            site_dict.setdefault('station_url',engine.stn_info.station_url)
            site_dict.setdefault('longitude',engine.stn_info.longitude_f)
            site_dict.setdefault('latitude',engine.stn_info.latitude_f)
            site_dict.setdefault('altitude',engine.stn_info.altitude_vt)
        except (ValueError,TypeError,IndexError) as e:
            logerr("location longitude latitude altitude %s" % e)

        # 'windDir10' is not defined in units.py
        weewx.units.obs_group_dict.setdefault('windDir10',
                   weewx.units.obs_group_dict.get('windDir','group_direction'))

        self.archive_queue = queue.Queue()
        self.archive_thread = RwsaThread(self.archive_queue, **site_dict)

        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)


class RwsaThread(weewx.restx.RESTThread):

    #_CONF_MAP = ('0Info=Regionalwetter-SA',
    #             '1Typ=1',
    #             '2Url=http://www.regionalwetter-sa.de/doebeln/get_daten.php',
    #             '3File=.\html\sa_dl_211.txt',
    #             '4Senddata=?valSA=',
    #             '5Separator=;',
    #             '6Unit=0',
    #             '7Userpw_md5=0',
    #             '8Success=OK',
    #             '9Version=2',
    #             'xBeginData')

    #                   variable, duration, aggregation, format
    _DATA_MAP = [       ('station','','attr','{}'),
                        ('zip_code','','attr','{}'),
                        ('state_code','','attr','{}'),
                        ('location','','attr','{}'),
                        ('latitude','','attr','{:.6f}'),
                        ('longitude','','attr','{:.6f}'),
                        ('lat_offset','','attr','{:.0f}'),
                        ('lon_offset','','attr','{:.0f}'),
                        ('username','','attr','{}'),
                        ('station_url','','attr','{}'), # URL Betreiber
                        ('station_model','','attr','{}'),
                        ('altitude','','attr','{:.0f}'),
                        ('weewx_version','','','{}'), # Software
                        ('dateTime','','','%d.%m.%Y'),
                        ('dateTime','','','%H:%M'),
                        ('outTemp','','','{:.1f}'),
                        ('outTempDayMax','','','{:.1f}'),
                        ('outTempDayMin','','','{:.1f}'),
                        ('outTemp1h','','','{:.1f}'),
                        ('','','','{:.f}'), # temp 5cm min
                        ('outHumidity','','','{:.0f}'),
                        ('barometer','','','{:.1f}'),        # QFF mbar
                        ('barometer','3h','diff','{:.1f}'),
                        ('dayRain','','','{:.1f}'),
                        ('windDir10','','','compass'),
                        ('windSpeed10','','','{:.1f}'),      # km/h
                        ('windGust','','','{:.1f}'),         # km/h
                        ('windGust','Day','max','{:.1f}'),    # km/h
                        ('dewpoint','','','{:.1f}'),
                        ('windchillDayMin','','','{:.1f}'),
                        ('','','','{:.1f}'), # sunshine today
                        ('','','','{}'), # URL Webcam
                        ('rain','Month','sum','{:.1f}'),
                        ('','','','{:.1f}'),
                        ('','','','{:.1f}'),
                        ('rain','Year','sum','{:.1f}'),
                        ('','','','{:.1f}'), # Regen Jahr Abw.
                        ('','','','{:.1f}'), # Regen Jahr Abw %
                        ('','','','{}'), # Schneehöhe
                        ('','','','%d.%m.%Y %H:%M'), # Ablesezeit Schnee
                        ('GTS','Day','last','{:.1f}'), # Grünlandtemperatur
                        ('GTSdate','Day','last','%d.%m.%Y'), # GLT 200 Datum
                        ('','','','%d.%m.%Y') # GLT 200 Vorjahr
                ]

    # Note: The units Regionalwetter Sachsen-Anhalt requests are not fully 
    # covered by one of the standard unit systems. See function 
    # __wns_umwandeln() for details.
    _UNIT_MAP = {'group_rain':'mm',
                 'group_rainrate':'mm_per_hour',
                 'group_speed':'km_per_hour'
                }
                
    def __init__(self, q, state_code, zip_code, username,
                 location='',station_model='',station_url='',
                 longitude=0,latitude=0,altitude='',
                 lon_offset=0,lat_offset=0,
                 station='Regionalwetter Sachsen-Anhalt', 
                 server_url=Rwsa.DEFAULT_URL,
                 skip_upload=False, manager_dict=None,
                 post_interval=None, max_backlog=sys.maxsize, stale=None,
                 log_success=True, log_failure=True,
                 timeout=60, max_tries=3, retry_wait=5,
                 log_url=False,T5CM=None,daySunD=None):
        super(RwsaThread, self).__init__(q,
                                          protocol_name='Rwsa',
                                          manager_dict=manager_dict,
                                          post_interval=post_interval,
                                          max_backlog=max_backlog,
                                          stale=stale,
                                          log_success=log_success,
                                          log_failure=log_failure,
                                          max_tries=max_tries,
                                          timeout=timeout,
                                          retry_wait=retry_wait)
        self.formatter=weewx.units.Formatter()
        self.station = station
        loginf("Station %s" % self.station)
        self.server_url = server_url
        loginf("Data will be uploaded to %s" % self.server_url)
        self.skip_upload = to_bool(skip_upload)
        self.log_url = to_bool(log_url)
        
        self.has_windDir10 = True
        
        self.username = str(username)
        
        # location description
        self.state_code = state_code
        self.zip_code = zip_code
        self.location = location
        loginf("Location %s, %s %s" % (location,state_code,zip_code))

        # station
        self.station_url = station_url
        self.station_model = station_model

        # location coordinates
        self.longitude = to_float(longitude)
        self.latitude = to_float(latitude)
        self.lon_offset = to_float(lon_offset)
        self.lat_offset = to_float(lat_offset)

        # station altitude
        try:
            self.altitude = weewx.units.convert(altitude,'meter')[0]
        except (ValueError,TypeError,IndexError):
            self.altitude=None
        loginf("Altitude %s ==> %.0f m" % (altitude,self.altitude))
        
        # 5cm temperature
        try:
            if T5CM and T5CM.lower()!='none':
                self._DATA_MAP[19] = (T5CM,'Day','min','{:.1f}')
        except Exception:
            pass
        
        # sunshine duration
        try:
            if daySunD and daySunD.lower()!='none':
                self._DATA_MAP[30] = (daySunD,'Day','sum','sunshine')
        except Exception:
            pass
        
        # report field names to syslog
        __x=""
        for __i in self._DATA_MAP:
            try:
                __x="%s (%s%s%s)" % (__x,__i[0],__i[1].capitalize(),__i[2].capitalize())
            except (TypeError,ValueError,IndexError):
                __x="%s (%s:*err*)" % (__x,__i)
        loginf("Fields: %s" % __x)

        # report unit map to syslog
        __x=""
        for __i in self._UNIT_MAP:
            __x="%s %s:%s" % (__x,__i,self._UNIT_MAP[__i])
        loginf("Special units:%s" % __x)

    def __wns_umwandeln(self,record):    
        # convert to metric units
        record_m = weewx.units.to_METRICWX(record)

        # temperature change for the last 1 hour
        if ('outTempDiff1h' not in record_m and
           'outTemp' in record_m and 'outTemp1h' in record_m):
            try:
                record_m['outTempDiff1h']=record_m['outTemp']-record_m['outTemp1h']
            except (TypeError,ValueError) as e:
                logerr("outTemp calc 1h diff: %s" % e)

        # barometer change for the last 1 hour
        if ('barometer1hDiff' not in record_m and 
            'barometer' in record_m and 'barometer1h' in record_m):
            try:
                record_m['barometer1hDiff']=record_m['barometer']-record_m['barometer1h']
            except (TypeError,ValueError) as e:
                logerr("barometer calc 1h diff: %s" % e)

        __data = []
        
        for key,vvv in enumerate(self._DATA_MAP):
            # archive column name
            rkey = "%s%s%s" % (vvv[0],
                               vvv[1].capitalize(),
                               vvv[2].capitalize())
            # format string
            fstr = vvv[3]
            
            if vvv[2]=='attr':
                # station data
                __data.append(fstr.format(getattr(self,vvv[0],'n.v.')))
            elif vvv[0] == 'weewx_version':
                # WeeWX version
                __data.append("WEEWX_%s" % (weewx.__version__))
            elif (rkey in record_m and record_m[rkey] is not None):
                # weather data
                try:
                    # Note: The units Regionalwetter Sachsen-Anhalt requests 
                    # are not fully covered by one of the standard unit systems.
                    
                    # get value with individual unit
                    __vt = weewx.units.as_value_tuple(record_m,rkey)
                    # if unit group (__vt[2]) is defined in _UNIT_MAP
                    # convert to the unit defined there
                    # check if we need to convert the unit
                    if __vt[2] in self._UNIT_MAP:
                        logdbg("%s convert unit from %.3f %s %s" % (rkey,__vt[0],__vt[1],__vt[2]))
                        __vt=weewx.units.convert(__vt,self._UNIT_MAP[__vt[2]])
                        logdbg("%s converted unit to %.3f %s %s" % (rkey,__vt[0],__vt[1],__vt[2]))
                    # format value to string
                    if __vt[2]=='group_time':
                        # date or time values
                        __data.append(time.strftime(fstr,
                                           time.localtime(record_m[rkey])))
                    elif fstr == 'sunshine':
                        if __vt[1]!='minute':
                            __vt = weewx.units.convert(__vt,'minute')
                        hour,min = divmod(__vt[0],60)
                        __data.append('%.0f:%02.0f' % (hour,min))
                    elif fstr == 'compass':
                        # compass direction
                        __data.append(self.formatter.to_ordinal_compass(__vt))
                    else:
                        # numeric values and strings
                        __data.append(fstr.format(__vt[0]))
                except (TypeError, ValueError, NameError, IndexError) as e:
                    logerr("%s:%s: %s" % (key,rkey,e))
                    __data.append('n.v.')
            else:
                __data.append('n.v.')
        return __data

    def format_url(self, record):
        """Return an URL for doing a POST to RWSA"""
        
        # create Regionalwetter Sachsen-Anhalt dataset
        __data = RwsaThread.__wns_umwandeln(self,record)
        
        # values concatenated by ';'
        __body = ";".join(__data)
        
        # replace special characters by % codes for URL
        __body = urllib.parse.quote(__body,safe='/;%:',encoding='iso8859-1')

        # build URL
        url = '%s?valSA=%s' % (self.server_url, __body)
        
        if self.log_url:
            loginf("url %s" % url)
        elif weewx.debug >= 2:
            logdbg("url: %s" % url)
        return url

#    def get_post_body(self, record):
#        """Specialized version for doing a POST to RWSA"""
#
#        __data = RwsaThread.__wns_umwandeln(self,record)
#        
#        xxx = "%s\n" % data[lkey] for lkey in data
#
#        zeilen=[]
#
#        for lkey in data:
#            zeilen.append("({} {})".format(lkey,data[lkey]))
#
#        trennz = '\n'
#        body = trennz.join(self._CONF_MAP)
#        body = body+trennz+trennz.join(__data[__lkey] for __lkey in __data)
#
#        datei = open('/tmp/wns.txt','w')
#        datei.write(body)
#        datei.close()
#
#        if weewx.debug >= 2:
#            logdbg("txt: %s" % body)
#
#        return body, 'text/plain'

    def get_record(self, record, dbmanager):
        """Augment record data with additional data from the archive.
        Should return results in the same units as the record and the database.
        
        returns: A dictionary of weather values"""
    
        # run parent class
        _datadict = super(RwsaThread,self).get_record(record,dbmanager)

        # actual time stamp
        _time_ts = _datadict['dateTime']
        _sod_ts = weeutil.weeutil.startOfDay(_time_ts)

        # 1 hour ago
        # We look for the database record nearest to 1 hour ago within +-5 min.
        # example:
        #   _time_ts = 15:35
        #   _ago_ts = 14:35 (if a record exists at that time, otherwise
        #             the time stamp of the nearest record)
        try:
            _result = dbmanager.getSql(
                    "SELECT MIN(dateTime) FROM %s "
                    "WHERE dateTime>=? AND dateTime<=?"
                    % dbmanager.table_name, (_time_ts-3600.0,_time_ts-3300.0))
            if _result is None:
                _result = dbmanager.getSql(
                    "SELECT MAX(dateTime) FROM %s "
                    "WHERE dateTime>=? AND dateTime<=?"
                    % dbmanager.table_name, (_time_ts-3900.0,_time_ts-3600.0))
            if _result is not None:
                _ago1_ts = _result[0]
            else:
                _ago1_ts = None
        except weedb.OperationalError:
            _ago1_ts = None
        
        # debugging output to syslog
        if weewx.debug >= 2:
            logdbg("get_record dateTime %s, Tagesanfang %s, vor 1h %s" %
                (time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.gmtime(_time_ts)),
                time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.gmtime(_sod_ts)),
                time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.gmtime(_ago1_ts))))

        # get midnight-to-midnight time span according to Tom Keffer
        daytimespan = weeutil.weeutil.archiveDaySpan(_time_ts)
        # yesterday
        yesterdaytimespan = weeutil.weeutil.archiveDaySpan(_time_ts,1,1)
        # get actual month
        monthtimespan = weeutil.weeutil.archiveMonthSpan(_time_ts)
        # get actual year
        yeartimespan = weeutil.weeutil.archiveYearSpan(_time_ts)
        # last 1, 3, 24 hours
        h1timespan = TimeSpan(_time_ts-3600,_time_ts)
        h3timespan = TimeSpan(_time_ts-10800,_time_ts)
        h24timespan = TimeSpan(_time_ts-86400,_time_ts)
        # last 10 minutes
        m10timespan = TimeSpan(_time_ts-600,_time_ts)
        
        try:
            # minimum and maximum temperature of the day
            # check for midnight, result is not valid then
            if ('outTempDayMax' not in _datadict and _sod_ts<_time_ts):
                _result = dbmanager.getSql(
                    "SELECT MIN(outTemp),MAX(outTemp),MIN(windchill),"
                    "MAX(UV) FROM %s "
                    "WHERE dateTime>? AND dateTime<=?"
                    % dbmanager.table_name, (_sod_ts,_time_ts))
                if _result is not None:
                    _datadict['outTempDayMin']=_result[0]
                    _datadict['outTempDayMax']=_result[1]
                    _datadict['windchillDayMin']=_result[2]
                    _datadict['UVDayMax']=_result[3]

            # temperature and barometer change of the last hour
            if _ago1_ts is not None:
                _result = dbmanager.getSql(
                    "SELECT outTemp,barometer,pressure FROM %s "
                    "WHERE dateTime=? and dateTime<=?"
                    % dbmanager.table_name, (_ago1_ts,_time_ts))
                if _result is not None:
                    if 'outTemp1h' not in _datadict:
                        _datadict['outTemp1h']=_result[0]
                    if 'barometer1h' not in _datadict:
                        _datadict['barometer1h']=_result[1]
                    if 'pressure1h' not in _datadict:
                        _datadict['pressure1h']=_result[2]
                    weewx.units.obs_group_dict.setdefault('outTemp1h','group_temperature')
                
                _result = dbmanager.getSql(
                    "SELECT MIN(windchill),MAX(radiation) FROM %s "
                    "WHERE dateTime>? and dateTime<=?"
                    % dbmanager.table_name, (_ago1_ts,_time_ts))
                if _result is not None:
                    if 'windchill1hMin' not in _datadict:
                        _datadict['windchill1hMin']=_result[0]
                    if 'radiation1hMax' not in _datadict:
                        _datadict['radiation1hMax']=_result[1]
                    weewx.units.obs_group_dict.setdefault('windchill1hMin','group_temperature')
                    weewx.units.obs_group_dict.setdefault('radiation1hMax','group_radiation')

        except weedb.OperationalError as e:
            log.debug("%s: Database OperationalError '%s'",self.protocol_name,e)
        except (ValueError, TypeError):
            pass

        # aggregation values
        for __key,__vvv in enumerate(self._DATA_MAP):
            # field name
            __obs=self._DATA_MAP[__key][0]
            # time span
            __tim=self._DATA_MAP[__key][1]
            # aggregation type
            __agg=self._DATA_MAP[__key][2]
            # aggregation field name
            __rky="%s%s%s" % (__obs,__tim.capitalize(),__agg.capitalize())
            # get aggregation if __tim and __agg are not empty
            if __tim!='' and __agg!='' and __rky not in _datadict:
                try:
                    # time span
                    if __tim=='1h':
                        __tts=h1timespan # 1 hour back from now
                    elif __tim=='3h':
                        __tts=h3timespan # 3 hours back from now
                    elif __tim=='24h':
                        __tts=h24timespan # 24 hours back from now
                    elif __tim=='Day':
                        __tts=daytimespan # the actual day local time
                    elif __tim=='Yesterday':
                        __tts=yesterdaytimespan # yesterday
                    elif __tim=='Month':
                        __tts=monthtimespan # the month the actual day is in
                    elif __tim=='Year':
                        __tts=yeartimespan # the year the actual day is in
                    else:
                        __tts=None
                    # get aggregate value
                    __result = weewx.xtypes.get_aggregate(__obs,__tts,__agg.lower(),dbmanager)
                    # convert to unit system of _datadict
                    _datadict[__rky] = weewx.units.convertStd(__result,_datadict['usUnits'])[0]
                    # register name with unit group if necessary
                    weewx.units.obs_group_dict.setdefault(__rky,__result[2])
                except Exception as e:
                    logerr("%s.%s.%s %s" % (__obs,__tim,__agg,e))
                
        # if 'windDir10' is not included in the record use 'windDir' instead
        if 'windDir10' not in _datadict and 'windDir' in _datadict:
            _datadict['windDir10'] = _datadict['windDir']
            if self.has_windDir10:
                logerr("'windDir10' is not present. Using 'windDir' instead.")
                self.has_windDir10 = False

        return _datadict
        
    def check_response(self,response):
        """Check the response from a HTTP post.
        
        check_response() is called in case, the http call returned
        success, only. That is for 200 <= response.code <= 299"""
    
        super(RwsaThread,self).check_response(response)
        
        #for line in response:
        #    loginf("response %s" % line)
        #raise FailedPost()
        
# Use this hook to test the uploader:
#   PYTHONPATH=bin python bin/user/regionialwetterSachsenAnhalt.py

if __name__ == "__main__":
    weewx.debug = 2

    try:
        # WeeWX V4 logging
        weeutil.logger.setup('Rwsa', {})
    except NameError:
        # WeeWX V3 logging
        syslog.openlog('Rwsa', syslog.LOG_PID | syslog.LOG_CONS)
        syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))

    q = queue.Queue()
    t = RwsaThread(q, api_key='123', station=0)
    t.start()
    r = {'dateTime': int(time.time() + 0.5),
         'usUnits': weewx.US,
         'outTemp': 32.5,
         'inTemp': 75.8,
         'outHumidity': 24,
         'windSpeed': 10,
         'windDir': 32}
    print(t.format_url(r))
    q.put(r)
    q.put(None)
    t.join(30)
