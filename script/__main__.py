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

LOGLINEPREFIX = 'CRON\[[0-9]+\]: \(.+\) CMD \(\s*'
LOGLINESUFFIX= '\)'
LOGDATEREGEX = '[A-Z][a-z]{2}\s+[0-9]+\s([0-9]{2}:){2}[0-9]{2}'
LOGDATEISMISSINGYEAR= True
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

def parseLogTimestamp(dateRegex, logLine):
  # parse syslog timestamp
  dateStr = re.search(dateRegex, logLine)
  # TODO: if regex failed (dateStr is None)
  # TODO: if parse string fails
  return datetime.strptime(dateStr.group(0), '%b %d %X')

def verboseOut(verbose, message):
  if verbose:
    print(message)

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
  cronCmd = args[1]
  cronTime = args[2]

  # Parse cron time spec
  cronEntry = CronTab(cronTime)
  lastExecution = datetime.utcnow() + timedelta(seconds=cronEntry.previous())
  verboseOut(options.verbose, 'theoretical last execution: ' + str(lastExecution))

  logfile = getLogfile(LOGPATH, lastExecution)
  verboseOut(options.verbose, 'logfile: ' + logfile['file'] + '; mtime: ' + str(datetime.fromtimestamp(logfile['mtime'])))

  # if oldest logfile is still newer than last execution date (could especially happen for crons with big intervals)
  if parseLogTimestamp(LOGDATEREGEX, getLogfileFirstLine(logfile['file']))  > lastExecution:
    unknown('oldest logfile is newer than last execution date')
  # no logfiles found with LOGPATH
  if logfile is None:
    unknown('no logfile found matching ' + LOGPATH)

  logline = grepLogfile(logfile['file'], LOGLINEPREFIX+cronCmd+LOGLINESUFFIX)
  # no matching line found in log
  if logline is None:
    critical('no execution found in ' + logfile['file'])
    verboseOut(options.verbose, 'logline:' + str(logline))

  lastLogged = parseLogTimestamp(LOGDATEREGEX, logline)
  # add year to date from logfile (ugly...)
  if LOGDATEISMISSINGYEAR:
    # TODO: handle logfile from 31.12 to 01.01
    # set missing year
    lastLogged = lastLogged.replace(year=datetime.fromtimestamp(logfile['mtime']).year)
    verboseOut(options.verbose, 'last logged:' + str(lastLogged))

  difference = abs(lastExecution - lastLogged)
  verboseOut(options.verbose, 'difference:' + str(difference))
  if difference >= timedelta(seconds=options.criticalThreshold):
    critical('last execution should have been at ' + str(lastExecution) + ', but was at ' + str(lastLogged))
  if difference >= timedelta(seconds=options.warningThreshold):
      warning('last execution should have been at ' + str(lastExecution) + ', but was at ' + str(lastLogged))
  else:
    ok('last execution was at ' + str(lastLogged))

if __name__ == "__main__":
  main(sys.argv)
