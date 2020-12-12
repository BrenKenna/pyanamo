#!/usr/bin/python


####################################################
####################################################
#
# SETUP
#
####################################################
####################################################


# Import modules
import boto3, random, string, time, sys, json, gzip
from boto3.dynamodb.conditions import Key, Attr
from subprocess import Popen, PIPE
from datetime import datetime
from pyanamo_functions import *
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')


# Parse input arguments
tbl = sys.argv[1]
data = sys.argv[2]
bundled = int(sys.argv[3])
if len(tbl) == 0 or len(data) == 0:
	print("\nExiting, no table or data argument supplied\n")

else:
	print("\nImport data into " + tbl + " from " + data + "\n")


# Import data into table
if bundled == 1:

	# Import Bundled
	print("\n\nRunning bundled import")
	response = importItemsBundled(tbl, data)
	for i in response:
		print(i)

else:
	# Import Normal
	print("\n\nRunning normal import")
	response = importItems(tbl, data)
	for i in response:
		print(i)
