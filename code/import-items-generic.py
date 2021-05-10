#!/usr/bin/python3


# Import modules
import argparse, boto3, random, string, time, sys, os, string, json, gzip
from boto3.dynamodb.conditions import Key, Attr
from subprocess import Popen, PIPE
from datetime import datetime
from pyanamo_functions import *
client = boto3.client('dynamodb', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')


###########################################
###########################################

# Parse input arguments

###########################################
###########################################


# Parse arguments
parser = argparse.ArgumentParser(description = "Create and import PyAnamo items from supplied file to the target DynamoDB table.\nFormat = 'TaskID|DynamoDB_Table|Task Script + Argument'\nOptional Nested tasks Format = 'TaskID|DynamoDB_Table|Task Script|Script Argument1,Argument2,Argument3,ArgumentN'", formatter_class = argparse.RawTextHelpFormatter)


# Arguments for code
parser.add_argument("-t", "--tbl", action = 'store', type = str, help = "DynamoDB target table\n")
parser.add_argument("-d", "--data", action = 'store', type = str, help = "Data to import\n")
parser.add_argument("-s", "--separator", action = 'store', type = str, help = "Delimiter separating table fields\n")
parser.add_argument("-n", "--nested", action = 'store', type = str, help = "Optional argument specifying delimiter on taskScript key for nesting within the table item\n")
args = parser.parse_args()
print(args)


# Exit if key argument are not supplied
if args.tbl == None or args.data == None or args.separator == None:

	# Exit if no table is provided
	print('\n\nExiting, key variables not provided\n')
	parser.print_help()
	sys.exit()

else:

	# Otherwise proceed
	tbl = args.tbl
	data = args.data
	separator = args.separator
	print('\n\nProceeding with import of ' + data + ' into table = ' + tbl + ' delimiter = ' + separator + '\n')


# Handle optional arguments
if args.nested == None:
	print('Importing items in single task mode')
	nested = 0

else:
	nested = 1
	nested_delim = args.nested
	print('Importing items in nested task mode, delimiter = ' + nested_delim)
del parser, argparse


# Read a file
def readFile(data):

	# Read supplied file
	with open(data, 'r') as f:
		data = [ line.rstrip('\n') for line in f ]
	f.close()
	return(data)


###########################################
###########################################

# Import data

###########################################
###########################################


# Connect and initialize list
table = dynamodb.Table(tbl)
itemList_import = []
importResponse = []


# Check table and import data
try:
    counter = int(client.describe_table(TableName = tbl)['Table']['ItemCount']) + 1
except:
    counter = 0

data = readFile(data)
if nested == 0:

	# Import as single items
	for i in data:

		# Set item variables
		itemID = int(i.split(separator)[0])
		taskID = str(i.split(separator)[1])
		tbl = str(i.split(separator)[2])
		taskScript = str(i.split(separator)[3]) + ' ' + str(i.split(separator)[4])

		# Create item
		item = {
			"itemID": int(itemID),
			"taskID": str(taskID),
			"InstanceID": "NULL",
			"TaskScript": str(taskScript),
			"lockID": 'NULL',
			"ItemState": 'todo',
			"Lock_Date": "NULL",
			"Done_Date": "NULL",
			"Log": {},
			"Log_Length": 0
		}

		# Import item
		itemList_import.append(item)
		response = table.put_item(Item = item, ReturnConsumedCapacity = 'TOTAL')
		importResponse.append(response)
		counter+=1
		print(response)


# Otherwise import nested items
else:

	# Import nested
	response = importItemsBundled(tbl, data, separator, nested_delim)
	for i in response:
		print(i)
