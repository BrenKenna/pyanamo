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
tbl = sys.argv[0]
data = sys.argv[1]
if len(tbl) == 0 or len(data) == 0:
	print("\nExiting, no table or data argument supplied\n")

else:
	print("\nImport data into " + tbl + " from " + data + "\n")


# Import data into table
response = importItems(tbl, data)
for i in response:
	print(i)
