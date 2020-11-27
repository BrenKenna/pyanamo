#!/usr/bin/python


# Load Required Modules
import os, sys, re
from zlib import *
import gridtools, couchdb


# Set Main Args
view = sys.argv[1]
DataFile = sys.argv[2]
taskID = sys.argv[3]
SM = taskID
soft = str("${TMPDIR}/pipeline/bin")


# Connect to couchDB
credentials.VIEW_NAME = view
db = gridtools.connect_to_couchdb()


# Skip token if exists
tokenname = str(str(SM) + "_" + str(view))
if tokenname in db:
	print("Skipping " + tokenname + " found in " + credentials.DBNAME)

else:

	# Template the task script
	taskScript = """bash ${soft}/${view}.sh ${DataFile} ${SM}"""
	taskScript = gridtools.templater(taskScript)

	# Define token
	token = {"_id": tokenname,
		"lock": 0,
		"done": 0,
		"type": view,
		"files": DataFile,
		"Task_ID": SM,
		"Task_Script": taskScript
	}

	# Upload
	print("Added Token = " + tokenname + " to Database = " + credentials.DBNAME + " under View =  " + credentials.VIEW_NAME)
	db.save(token)
