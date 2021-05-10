#!/usr/bin/python3
# 
# - Make part of client?
# 
# 

# Import modules
import argparse, boto3, random, string, time, sys, os, string, json, gzip
from boto3.dynamodb.conditions import Key, Attr
import pyanamo_functions as pf


# Parse input args
table = sys.argv[1]
Niterations = sys.argv[2]
waitTime = sys.argv[3]


# Connect to dynamo
dynamo_client = boto3.client('dynamodb', region_name = 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
table = dynamodb.Table(table)

# Monitor state summaries over time
N = int(Niterations)
while N >= 1:

	# Get State Summary dict
	itemData = pf.itemCounter(table)
	itemSum = sum([ len(itemData[i]) for i in itemData.keys() ])
	data = [ str( 'Total = ' + str(itemSum) ) ]

	# Print current state summary
	data.extend([ str(i + " = " + str(len(itemData[i]))) for i in itemData.keys() ])
	sys.stdout.write(str(", ".join(data) + '\n'))

	# Decrement and wait
	N -= 1
	time.sleep(int(waitTime))
