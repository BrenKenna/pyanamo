#!/usr/bin/python


# Import modules
import boto3, time, string, random, re, os, time, sys, json, gzip
from datetime import datetime
import client as pc
import modifier as pm
import executor
import runner
import multiprocessing as mp


# Parallelize nested item processing
def parallel_nested(todo_item):

	# Stagger start times of current process
	N = float(random.randint(1, 30) / 100)
	N_2 = float(random.randint(1, 20) / 100)
	N_3 = float(random.randint(1, 10) / 100)
	time.sleep(N + N_2 + N_3)


	# Setup dynamo session for table
	dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
	table = dynamodb.Table('Testing')


	# Instantiate PyAnamo Runner without getting new todoDict
	pyanamoRunner = runner.PyAnamo_Runner(table, 'bkennatesting')
	pyanamoRunner.handleNestedItem(todo_item)


# Sub-classes to allow single item pool to spawn a pool for nested items
class NoDaemonProcess(mp.Process):
	def _get_daemon(self):
		return False
	def _set_daemon(self, value):
		pass
	daemon = property(_get_daemon, _set_daemon)

class NoDaemonContext(type(mp.get_context())):
    Process = NoDaemonProcess

class PyAnamo_ProcessPool(mp.pool.Pool):
	def __init__(self, *args, **kwargs):
		kwargs['context'] = NoDaemonContext()
		super(PyAnamo_ProcessPool, self).__init__(*args, **kwargs)


# Nested items
def nested_items(nested_item, Nprocesses):

	# Initialize multiprocessing pools: N or mp.cpu_count()
	availableThreads = mp.cpu_count()
	pool = PyAnamo_ProcessPool(Nprocesses)

	# Split list across N chunks
	chunks = [ list(nested_item['TaskScript'].keys())[i:i+Nprocesses] for i in range(0, len(nested_item['TaskScript'].keys()), Nprocesses) ]


	# Compose todo_item dicts for each parallel pool
	para_list = [ ]
	for chunk in chunks:

		# Re-create todo_item dict for each required process
		data = {}
		for todoKey in nested_item.keys():
			data.update( {todoKey: nested_item[todoKey]} )
			data['TaskScript'] = {}

			# Add the nested task data to the appropriate task script
			for task in chunk:
				data['TaskScript'].update( { task: nested_item['TaskScript'][task] } )

		# Add dict to the process list
		para_list.append(data)


	# Run processes
	pool.map(parallel_nested, para_list)
	pool.close()
	pool.join()


# Run
def main(Nprocesses, nested_item = None):

	# Run parallel_items
	if nested_item != None and Nprocesses > 1:

		# Call nested item function
		nested_items(nested_item, Nprocesses)

	# Otherwise exit
	else:
		print('\nError, no dict or process count > 1 provided for nested item processing\n')
