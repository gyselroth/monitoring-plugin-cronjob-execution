#!/bin/python
from crontab import CronTab
from datetime import datetime
from datetime import timedelta
from glob import glob
from os import stat
from optparse import OptionParser
import re
import sys
import gzip

LOGLINEPREFIX = r'CRON\[[0-9]+\]: \(.+\) CMD \(\s*'
LOGLINESUFFIX = r'\)'
LOGDATEREGEX = r'[A-Z][a-z]{2}\s+[0-9]+\s([0-9]{2}:){2}[0-9]{2}'
LOGDATEISMISSINGYEAR = True
LOGPATH = '/var/log/syslog*'
CRITICAL = 3600
WARNING = 1800

def ok(message):
  print('OK - ' + message)
  exit(0)

def warning(message):
  print('WARNING - ' + message)
  exit(1)

def critical(message):
  print('CRITICAL - ' + message)
  exit(2)

def unknown(message):
  print('UNKNOWN - ' + message)
  exit(3)

def getLogfile(logPath, lastExecution):
  # get all logfiles
  files = glob(logPath)
  # create list with filename and mtime
  files = list(map(lambda file: {'file': file, 'mtime': stat(file).st_mtime}, files))
  # sort list by mtime
  files.sort(key=lambda k: k['mtime'])
  # get oldest file which is newer than lastExecution
  logfile = None
  for entry in files:
    timestamp = datetime.fromtimestamp(entry['mtime'])
    if lastExecution < timestamp:
      logfile = entry
      break
  return logfile

def getLogfileFirstLine(logfile):
  with readLogFile(logfile) as file:
    return file.readline()

def readLogFile(logfile):
  if re.search('.*\.gz$', logfile):
    return gzip.open(logfile, 'rt')
  return open(logfile, 'r')

def grepLogfile(logfile, regex):
  # get newest matching line of logfile
  foundLine = None
  for line in readLogFile(logfile):
    if re.search(regex, line):
      foundLine = line
  return foundLine

def parseLogTimestamp(dateRegex, logLine, year=None):
  # parse syslog timestamp
  dateStr = re.search(dateRegex, logLine)
  # TODO: if regex failed (dateStr is None)
  # TODO: if parse string fails
  # add year to date from logfile (ugly...)
  timestamp = datetime.strptime(dateStr.group(0), '%b %d %X')
  if LOGDATEISMISSINGYEAR:
    # TODO: handle logfile from 31.12 to 01.01
    # set missing year
    if not year:
        Error("year has to be set")
    timestamp = timestamp.replace(year=year)
  return timestamp

def verboseOut(verbose, message):
  if verbose:
    print(message)

def shellUnescape(string):
    string = re.sub(r'(?<!\\)\\', r'', string)
    string = re.sub(r'\\\\', r'\\', string)
    return string

def cronPercentUnescape(string):
    return re.sub(r'\\%', r'%', string)

def parseInputCommand(string):
    return cronPercentUnescape(shellUnescape(string))

def main(argv):
  # Parse options
  usage = "usage: %prog [options] <cron commandline> <cron datedefinition>"
  parser = OptionParser(usage=usage)
  parser.add_option('-c', dest='criticalThreshold', type=int, default=CRITICAL, help='threshold for critical in SECONDS', metavar='SECONDS')
  parser.add_option('-w', dest='warningThreshold', type=int, default=WARNING, help='threshold for warning in SECONDS', metavar='SECONDS')
  parser.add_option('-v', dest='verbose', default=False, help='verbose output', action='store_true')
  (options, args) = parser.parse_args(args=argv)
  # Parse arguments
  if len(args) < 3:
    unknown('arguments missing: ' + parser.get_usage())
  cronCmd = parseInputCommand(args[1])
  cronTime = args[2]
  verboseOut(options.verbose, 'cron command: ' + str(cronCmd))

  # Parse cron time spec
  try:
    cronEntry = CronTab(cronTime)
  except ValueError as error:
    unknown('error parsing time specification: ' + str(error))

  now = datetime.now()
  lastExecution = now + timedelta(seconds=cronEntry.previous(now=now, default_utc=True))
  verboseOut(options.verbose, 'theoretical last execution: ' + str(lastExecution))

  # find logfile
  logfile = getLogfile(LOGPATH, lastExecution)
  if(logfile is None):
    unknown('no logfile found for the time in question: ' + str(lastExecution))
  verboseOut(options.verbose, 'logfile: ' + logfile['file'] + '; mtime: ' + str(datetime.fromtimestamp(logfile['mtime'])))

  # check found logfile
  logYear = datetime.fromtimestamp(logfile['mtime']).year if LOGDATEISMISSINGYEAR else None
  logStart =  parseLogTimestamp(LOGDATEREGEX, getLogfileFirstLine(logfile['file']), year=logYear)
  verboseOut(options.verbose, 'log start: ' + str(logStart))
  # if oldest logfile is still newer than last execution date (could especially happen for crons with big intervals)
  if logStart > lastExecution:
    unknown('oldest logfile is newer than last execution date')
  # no logfiles found with LOGPATH
  if logfile is None:
    unknown('no logfile found matching ' + LOGPATH)

  logline = grepLogfile(logfile['file'], LOGLINEPREFIX+re.escape(cronCmd)+LOGLINESUFFIX)
  # no matching line found in log
  if logline is None:
    verboseOut(options.verbose, 'regex: ' + LOGLINEPREFIX+re.escape(cronCmd)+LOGLINESUFFIX)
    critical('no execution found in ' + logfile['file'])
  verboseOut(options.verbose, 'logline: ' + str(logline))

  lastLogged = parseLogTimestamp(LOGDATEREGEX, logline, year=logYear)
  verboseOut(options.verbose, 'last logged: ' + str(lastLogged))

  difference = abs(lastExecution - lastLogged)
  verboseOut(options.verbose, 'difference: ' + str(difference))
  if difference >= timedelta(seconds=options.criticalThreshold):
    critical('last execution should have been at ' + str(lastExecution) + ', but was at ' + str(lastLogged))
  if difference >= timedelta(seconds=options.warningThreshold):
      warning('last execution should have been at ' + str(lastExecution) + ', but was at ' + str(lastLogged))
  else:
    ok('last execution was at ' + str(lastLogged))

if __name__ == "__main__":
  main(sys.argv)
