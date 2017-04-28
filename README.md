# Monitoring Plugin: Cronjob last execution

### Description
Check if the last execution of a given cronjob was at the time it should have been

### Usage
Usage: check_cron_lastexecution [options] <shell escaped cron command> <cron datedefinition>

Options:
  -h, --help  show this help message and exit
  -c SECONDS  threshold for critical in SECONDS [Default: 3600]
  -w SECONDS  threshold for warning in SECONDS [Default: 1800]
  -v          verbose output

### Example
```
./check_cron_lastexecution "test\ -x\ /usr/sbin/anacron\ \|\|\ \(\ cd\ /\ \&\&\ run-parts\ --report\ /etc/cron.daily\ \)" "25 6 * * *"
OK - last execution was at 2017-04-27 06:53:01
```

### Build
* before the build, some constants in `script/__main__.py` (LOG*) may have to be adapted to match your environment
```
./build.sh
```

### Install 
* Copy check_cron_lastexecution to all your servers
* This check is required to run on the checked host itself therefore you need to remotely excute this check via nrpe, ssh or something similar.
* create a service/exec in your monitoring engine to execute the remote check
