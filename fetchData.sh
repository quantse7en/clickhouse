#!/bin/bash

# Activate virtual environment
source /home/ubuntu/zz/clkh_env/bin/activate

# Move to script directory
cd /home/ubuntu/zz/script

# Check if two arguments are provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <startdate> <enddate>"
    exit 1
fi

STARTDATE=$1

# If enddate not given, use today's date
if [ -z "$2" ]; then
    ENDDATE=$(date +%Y-%m-%d)
else
    ENDDATE=$2
fi


# Run the Python script with the arguments
python3 fetchData.py "$STARTDATE" "$ENDDATE"