# -*- coding: utf-8 -*-

from datetime import datetime as datetime
from datetime import timedelta

def nowUTC():
    return datetime.now()

def convertUTCtoCET(dt_utc):
    from pytz_zip.gae import pytz_zip
    UTC_ZONE = pytz_zip.timezone('UTC')
    CET_ZONE = pytz_zip.timezone('Europe/Amsterdam')  # pytz.timezone('CET')
    return dt_utc.replace(tzinfo=UTC_ZONE).astimezone(CET_ZONE)

def nowCET():
    utc = nowUTC()
    return convertUTCtoCET(utc)

#'%H:%M:%S.%f'
#'%H:%M:%S'
def datetimeStringCET(dt=None, seconds=False, format = None):
    if dt == None:
        dt = nowUTC()
    dt_cet = convertUTCtoCET(dt)
    if format == None:
        format = '%d-%m-%Y %H:%M:%S' if seconds else '%d-%m-%Y %H:%M'
    return dt_cet.strftime(format)

def dateString(dt=None, format = '%d-%m-%Y'):
    if dt == None:
        dt = nowUTC()
    return dt.strftime(format)

def getCurrentYearCET():
    dt_cet = convertUTCtoCET(nowUTC())
    return int(dt_cet.strftime('%Y'))
###

def get_midnight(date = None):
    if date == None:
        date = nowCET()
    return date.replace(hour=0, minute=0, second=0, microsecond=0)

def delta_min(dt1, dt2):
    diff = dt2 - dt1
    min_sec = divmod(diff.days * 86400 + diff.seconds, 60) # (min,sec)
    return min_sec[0]

def delta_days(dt1, dt2):
    diff = dt2 - dt1
    return diff.days

def ellapsed_min(dt):
    return delta_min(dt, nowUTC())

def get_datetime_add_days(days, dt = None):
    if dt == None:
        dt = nowUTC()
    return dt + timedelta(days=days)

def get_datetime_days_ago(days, dt = None):
    if dt == None:
        dt = nowUTC()
    return dt - timedelta(days=days)

def get_datetime_hours_ago(hours, dt = None):
    if dt == None:
        dt = nowUTC()
    return dt - timedelta(hours=hours)

def isTimeFormat(time_string):
    try:
        datetime.strptime(time_string, '%H:%M')
        return True
    except ValueError:
        return False

def getDatetime(date_string, format='%d%m%Y'):
    try:
        date = datetime.strptime(date_string, format)
    except ValueError:
        return None
    return date

def removeTimezone(dt):
    return dt.replace(tzinfo=None)

def getDateFromDateTime(dt = None):
    if dt == None:
        dt = nowUTC()
    return datetime.date(dt)

def getMinutes(input):
    t1 = datetime.strptime(input, '%H:%M')
    t2 = datetime.strptime('00:00', '%H:%M')
    return int((t1-t2).total_seconds()//60)

