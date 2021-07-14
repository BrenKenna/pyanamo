#!/usr/bin/python3


# Import modules
import sys, json, time
import manager as pmanager


# Parse input
user_data = {
	"table_name": sys.argv[1],
	"aws_region": sys.argv[2],
	'data': sys.argv[3],
	'delim': sys.argv[4],
	'nested_delim': None
}


# Add nested delimiter if provided
if len(sys.argv) > 5:
	user_data['nested_delim'] = sys.argv[5]


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
