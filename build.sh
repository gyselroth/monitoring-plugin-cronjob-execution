#!/bin/sh

if [ -d parse-crontab ]
then
    cd parse-crontab
    # update parse-crontab
    echo "# update parse-crontab"
    git pull origin master
else
    # clone parse-crontab
    echo "# clone parse-crontab"
    git clone https://github.com/josiahcarlson/parse-crontab
    cd parse-crontab
fi

# build parse-crontab to check_cron_lastexecution directory
echo "# build parse-crontab to check_cron_lastexecution directory"
python setup.py build --build-purelib ../script/

cd ../script
# zip check_cron_lastexecution directory
echo "# zip check_cron_lastexecution directory"
tmp=$(mktemp -u --suffix=.zip /tmp/$0.XXXXXX)
zip -r $tmp *

cd ..
# generate executable
echo "# generate executable"
echo '#!/usr/bin/env python' | cat - $tmp > check_cron_lastexecution
chmod +x check_cron_lastexecution
ls check_cron_lastexecution

# cleanup
echo "# cleanup"
rm $tmp
