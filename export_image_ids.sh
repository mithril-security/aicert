#!/bin/bash

ID=$(docker images -q --no-trunc $1) 
ROW="{\"@local/$1\": \"$ID\"}"

FILE=$(cat container_ids.json)

if [ -z "$FILE" ]
then
    echo $ROW  > container_ids.json
else
    echo $FILE | jq ". + $ROW" > container_ids.json
fi

