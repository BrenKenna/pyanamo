#!/usr/bin/python3


# Import modules
import argparse
import sys, json, time
import manager as pmanager


################################################
################################################
# 
# Handle Arguments
# 
################################################
################################################


# Parse arguments
parser = argparse.ArgumentParser(description = """Import a list of items into the supplied DynamoDB table from a file. The specified DynamoDB table is created if it does not exists. The input file must adhere to the standardized PyAnamo schema. The format for the input file is shown below and must include the header. The field delimiter must be provided, whereas the nested task delimiter is an optional argument.

Example Input Data Format:

	itemID|TaskID|TaskScript|TaskArgs
	SRR6776829_TARDBP_FUS|SRR6776829|bash ${PIPELINE}/HaplotypeCaller.sh SRR6776829|chr1:11012344-11030528,chr16:31180138-31191605

	Field Delimiter = '|' or ',' or '\\t' or ';' etc
	OPTIONAL Nested task delimiter = ','
""", formatter_class = argparse.RawTextHelpFormatter)


# Arguments for code
parser.add_argument("-t", "--table_name", action = 'store', type = str, help = "DynamoDB table to query\n")
parser.add_argument("-i", "--input_data", action = 'store', type = str, help = "Text file containing the items to import into the supplied DynamoDB Table\n")
parser.add_argument("-d", "--field_delimiter", action = 'store', type = str, help = "The field delimiter of the input data \n")
parser.add_argument("-r", "--aws_region", action = 'store', type = str, help = "AWS region that the dynamo table is in\n")
parser.add_argument("-n", "--nested_delimiter", action = 'store', type = str, help = "Optional Argument: Delimiter separating the nested task arguments\n")
args = parser.parse_args()


# Exit if key argument are not supplied
if args.table_name == None or args.input_data == None or args.field_delimiter == None or args.aws_region == None:

	# Exit if no table is provided
	sys.stdout.write('\n\nExiting, key argumets not provided. Required arguments are DynamoDB Table Name, a file, field delimiter of file and AWS Region of the DynamoDB Table\n')
	parser.print_help()
	sys.exit()


# Otherwise proceed to parsing arguments
else:
	user_data = {
		'table_name': args.table_name,
		'aws_region': args.aws_region,
		'data': args.input_data,
		'delim': args.field_delimiter,
		'nested_delim': None
	}

# Handle optional arguments
if args.parallel_items != None:
	user_data['nested_delim'] = args.nested_delimiter

del parser, argparse, args

##################################################
##################################################
# 
# Import items into table
# 
##################################################
##################################################


# Check table
manager_client = pmanager.PyAnamo_Manager(dynamo_table = user_data['table_name'], region = user_data['aws_region'])
tableExists = manager_client.check_table(user_data['table_name'])
if tableExists == 0:
	tableCreated = manager_client.create_workflow_table(user_data['table_name'])


# Wait for table to be created
for i in range(0, 5):
	try:
		manager_client.handle_DynamoTable(user_data['table_name'])
		out = manager_client.getToDoItems('todo', recursively = 0, pyanamo_fields = None)

	except:
		print('\n\nWaiting for table to be configured\n')
		time.sleep(10)


# Import data
out = manager_client.import_from_file(
	table_name = user_data['table_name'],
	data = user_data['data'],
	delim = user_data['delim'],
	nested_delim = user_data['nested_delim']
)


# Log import
print(json.dumps(out['Items'], indent = 4))
print('Import N items = ' + str(out['N']))
