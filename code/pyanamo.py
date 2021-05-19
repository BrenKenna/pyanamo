#!/usr/bin/python


####################################################
####################################################
#
# SETUP
#
####################################################
####################################################


# Import modules
import argparse, boto3, string, time, sys, os, string
import client as pc
import modifier as pm
import executor
import runner
import parallel_processes


# Exit if environmental variables are not defined
try:
	pyanamo = os.environ['PYANAMO']

except:
	sys.stderr.write("\n\nExiting, global variable for PYANAMO not found")
	sys.exit()


# Try get instanceID
try:
	sys.stdout.write(str("\n\nAWS-Batch ID = " + os.environ['AWS_BATCH_JOB_ID'].replace(':', '_')))

except:
	sys.stderr.write("\n\nError getting aws batch jobID, falling back to EC2-InstanceID and IP\n")


####################################################
####################################################
# 
# PARSE INPUT ARGUMENTS
# 
####################################################
####################################################


# Parse arguments
parser = argparse.ArgumentParser(description = "Pilot job framework to iterate over items in the supplied DynanmoDB table.\nIncludes argument to facilitate processing nested items, or running in auto-detect mode.", formatter_class = argparse.RawTextHelpFormatter)

# Handle conflicting arguments
group = parser.add_mutually_exclusive_group()
group.add_argument("-v", "--verbose", action = "store_true")
group.add_argument("-q", "--quiet", action = "store_true")

# Arguments for code
parser.add_argument("-t", "--table_name", action = 'store', type = str, help = "DynamoDB table to query\n")
parser.add_argument("-r", "--aws_region", action = 'store', type = str, help = "AWS region that the dynamo table is in\n")
parser.add_argument("-b", "--bucket", action = 'store', type = str, help = "S3 Bucket for logs >1GB\n")
parser.add_argument("-k", "--bucket_Key", action = 'store', type = str, help = "Path on the S3 bucket for PyAnamo to put gzip compressed log files\n")
parser.add_argument("-i", "--parallel_items", action = 'store', type = int, help = "Optional Argument: Number of parallel processes to fetch todo items\n")
parser.add_argument("-n", "--parallel_nests", action = 'store', type = int, help = "Optional Argument: Number of parallel processes to act on nested items\n")
parser.add_argument("-w", "--wall_time", action = 'store', type = str, help = "Optional Argument: Wall time in hours to stop pyanamo from fetching the next todo item / task\n")
args = parser.parse_args()


# Exit if key argument are not supplied
if args.table_name == None or args.bucket == None or args.aws_region == None:

	# Exit if no table is provided
	sys.stdout.write('\n\nExiting, key variables not provided. Required arguments are DynamoDB Table Name, S3 Bucket Name and AWS Region of the DynamoDB Table\n')
	parser.print_help()
	sys.exit()


# Otherwise proceed
else:

	table_name = args.table_name
	s3Bucket = args.bucket
	aws_region = args.aws_region
	bucketKey = args.bucketKey
	timeLimit = args.wall_time
	sys.stdout.write('\n\nProceeding with table = ' + table_name + '\n')


# Handle optional arguments
if args.parallel_items == None or args.parallel_items == 1:
	sys.stdout.write('\nRunning single process to fetch todo items\n')
	parallel_items = 0

else:
	parallel_items = args.parallel_items
	sys.stdout.write('\nRunning ' + str(parallel_items) + ' processes to fetch todo items\n')

if args.parallel_nests == None or args.parallel_nests == 1:
	sys.stdout.write('\nRunning single process to handle nested items\n')
	parallel_nests = 0

else:
	parallel_nests = args.parallel_nests
	sys.stdout.write('\nRunning ' + str(parallel_nests) + ' processes for nested items\n')
del parser, argparse, args


######################################################################
######################################################################
#
# EXECUTE THE PYANAMO ENGINE
#
######################################################################
######################################################################


# Determine how to run application
if parallel_items > 1:

	# Set kwargs for PyAnamo Runner
	aws_kwargs = {
		"region": aws_region,
		"dynamo_table": table_name,
		"s3_key": s3Bucket,
		"timeLimit": timeLimit,
	}

	# Parallel mode
	sys.stdout.write('\nDelgating PyAnamo Runner instantiation\n')
	parallel_processes.singleItem_main(parallel_items, Nested_Processes = parallel_nests, aws_kwargs = aws_kwargs)


# Single processes
else:

	# Setup
	sys.stdout.write('\nConfiguring dynamo table with ' + table_name + '\n')
	dynamodb = boto3.resource('dynamodb', region_name = aws_region)
	table = dynamodb.Table(table_name)


	# Instatiate PyAnamo runner
	sys.stdout.write('\nExecuting PyAnamo Runner\n')
	pyanamoRunner = runner.PyAnamo_Runner(table, s3Bucket, Parallel_Nests = parallel_nests, aws_region = aws_region, timeLimit = timeLimit, todoDict = 'get')
	logging = pyanamoRunner.processItems()
