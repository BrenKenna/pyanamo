####################################
####################################
# 
# Test Runner
# 
####################################
####################################


# Test the runner module
python
import boto3, time, string, random, re, os, time, sys, json, gzip
from datetime import datetime
import client as pc
import modifier as pm
import executor
import runner


# Initialize dynamoDB table
dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
table = dynamodb.Table('Testing')


# Construct pyanamoRunner for task table
pyanamoRunner = runner.PyAnamo_Runner(table, 'herp_a_derp', todoDict = 'get', Parallel_Nests = 2)


# Process all tasks
pyanamoRunner.processItems()
