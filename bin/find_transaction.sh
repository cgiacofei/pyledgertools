#! /bin/sh

tmpfile=$(mktemp /tmp/found_XXXXX.ledger)
trap "rm -rf $tmpfile" EXIT

INPUT=$(echo $1 | sed 's/\s/\\s/g')
DIR=$(dirname $(sed 's/--file\s\+\(.*\)/\1/g' ~/.ledgerrc))
DIR="${DIR/#\~/$HOME}"
cd $DIR
echo ';; Located Transactions' > $tmpfile
echo > $tmpfile
cat *.ledger | sed 's/^\([0-9]\+.*\)/--\1/' | awk 'BEGIN { RS="--" } ; /'${INPUT}'/ {print}' >> $tmpfile

vim $tmpfile
