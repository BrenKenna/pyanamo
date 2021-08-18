######################################################
######################################################
# 
# How to Manage the Task Logs in PyAnamo:
# 
# 	- We want 2 things:
# 		i). A list of gVCFs that were called
#  		ii). Which tasks failed and ca be restarted
# 
######################################################
######################################################


############################################
############################################
# 
# Get Both Information For 1 Example Item
# 
############################################
############################################


# Ultimate setup we want
progress_check = { 'Completed': {}, 'Failed': [ ] }


# Get done items
done_logs = manager_client.getToDoItems('done', recursively = 0, pyanamo_fields = 'itemID, TaskID, Nested_Tasks, Log_Length, Log, ItemState')


# Test on a single sample
itemData = done_logs['Items'][1]
itemID = itemData['itemID']


# Manage failed tasks for each item
sample_Failed = {
	'itemID': itemID,
	'TaskScript': {}
}


# Manage completed tasks for each item
sample_Completed = {
	itemID: []
}


# Iteratively check the items logs
for task in itemData['Log'].keys():
	task_log = itemData['Log'][task]['stdout']
	if len( task_log.split('\n') ) > 1:
		failed_task = {task: {}}
		sample_Failed['TaskScript'].update( failed_task )
	else:
		if len( task_log.split('\t') ) != 7:
			failed_task = {task: {}}
			sample_Failed['TaskScript'].update( failed_task )
		else:
			sample_Completed[itemID].append(task_log)



# Add the active items failed tasks to our main gig
progress_check['Failed'].append(sample_Failed)
progress_check['Completed'].update(sample_Completed)




###################################################
###################################################
# 
# Organize All of Our Work:
#  
# 	a). A list of items + their tasks to restart
# 
# 	b). A list of gVCFs to add to CMS
# 
###################################################
###################################################



# Get done items
done_logs = manager_client.getToDoItems('done', recursively = 0, pyanamo_fields = 'itemID, TaskID, Nested_Tasks, Log_Length, Log, ItemState')


# Create an object to hold all data
progress_check = { 'Completed': {}, 'Failed': [ ] }


# Test on a single sample
for itemData in done_logs['Items']:
	itemID = itemData['itemID']
	sample_Failed = {
		'itemID': itemID,
		'TaskScript': {}
	}
	sample_Completed = {
		itemID: []
	}
	for task in itemData['Log'].keys():
		task_log = itemData['Log'][task]['stdout']
		if len( task_log.split('\n') ) > 1:
			failed_task = {task: {}}
			sample_Failed['TaskScript'].update( failed_task )
		else:
			if len( task_log.split('\t') ) != 7:
				failed_task = {task: {}}
				sample_Failed['TaskScript'].update( failed_task )
			else:
				sample_Completed[itemID].append(task_log)
	if len(sample_Failed['TaskScript']) != 0:
		progress_check['Failed'].append(sample_Failed)
		progress_check['Completed'].update(sample_Completed)
	else:
		progress_check['Completed'].update(sample_Completed)



# Reset these guys
# manager_client.reset_itemNests(table_name, itemList = progress_check['Failed'])




########################################
########################################
# 
# Updating an SQL DB in python
# 
########################################
########################################


# Import sqlite package
import sqlite3
from sqlite3 import Error


# Create database connection
db = '/tmp/pipeline/TOPMed_Calling/topmed_calling.db'
con = sqlite3.connect(db)


# Create table
query = str('CREATE TABLE IF NOT EXISTS topmed_calling(SampleID VARCHAR(250), chromosome VARCHAR(10), Column_Check text, Exome_Lines INT(50), Exome_Variants INT(50), Exome_GQ_Summary text, Data_File_Size VARCHAR(50), gVCF_Path text, PRIMARY KEY(SampleID, chromosome)); ')
cur = con.cursor()
cur.execute(query)



# Check schema: 	Use linux instead
cur = con.cursor()
query = str("PRAGMA table_info('topmed_calling')")
response = cur.execute(query)

for i in response:
	print(i)



# Setup test data for insert: 	A list of tuples
SampleID = 'SRR9248287'
test_data = progress_check['Completed'][SampleID]
updates = [ tuple( str( SampleID + '\t' + i).split('\t') ) for i in test_data ]



# Insert test data
query = str('INSERT INTO topmed_calling(SampleID, chromosome, Column_Check, Exome_Lines, Exome_Variants, Exome_GQ_Summary, Data_File_Size, gVCF_Path) VALUES(?, ?, ?, ?, ?, ?, ?, ?);')
cur = con.cursor()
cur.executemany(query, updates)
con.commit()


# Check insert
cur = con.cursor()
query = str('select * from topmed_calling limit 4;')
cur.execute(query)
task_summary = []
for i in cur.fetchall():
	task_summary.append(i)


# View results
for i in task_summary:
	print(i)



# Try to insert the same data
query = str('INSERT INTO topmed_calling(SampleID, chromosome, Column_Check, Exome_Lines, Exome_Variants, Exome_GQ_Summary, Data_File_Size, gVCF_Path) VALUES(?, ?, ?, ?, ?, ?, ?, ?);')
cur = con.cursor()
cur.executemany(query, updates)


"""

- Example error

Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
con.commit()
sqlite3.IntegrityError: UNIQUE constraint failed: topmed_calling.SampleID, topmed_calling.chromosome


"""



########################################
########################################
# 
# Write & Read JSON
# 
########################################
########################################



# Copy example file from mine-ui
"""

scp -i ~/.ssh/dbgap-ami-topmed.pem ~/sql-import-example.json  ec2-user@ec2-35-172-121-232.compute-1.amazonaws.com:/tmp/pipeline/TOPMed_Calling/sql-import-example.json 

"""


# Write a dictionary to a JSON file
import json
with open('/tmp/pipeline/TOPMed_Calling/sql-import-example.json', 'w') as Write_Out_Json:
	json.dump(progress_check, Write_Out_Json)



# Read in test example
import manager as pmanager
data = '/tmp/pipeline/TOPMed_Calling/sql-import-example.json'
table_name = 'Testing'
aws_region = 'us-east-1' 
manager_client = pmanager.PyAnamo_Manager(
    dynamo_table = table_name,
    region = aws_region
)
data = manager_client.read_jsonFile(data)

