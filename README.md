# PyAnamo


## Introduction
The purpose of *PyAnamo* is to automate "Big Data" *'Extraction Transformation and Loading'* procedures, ETLs, on AWS using Batch &amp; DynamoDB. The principal of operation is that each requested EC2 instance executes an application that iterates over a list of work to do, *tasks*, which are stored in a database. The database is populated with various collections of tasks that represent all of the work to do from your favourite workflow. Where each individual *collection* is a step of your workflow. The database can then be queried to monitor progress of each step of the workflow.

Each task for a given collection has a *"Task Script"* key whose value is executed by a *Generic PyAnamo Application*. The setup allows for each instance of the application, running across the cluster of size N, to iteratively execute *'Program A'* on all tasks in the collection of *'Workflow Step A'*. The application could also be potentially ported into existing setups at the users own discretion, ex 'https://doi.org/10.1093/bioinformatics/btz379'.

The **advantage** in storing all of the tasks in a database, specifically for ***Population Based Reseqeucning Studies***, is that there can be ***ten's of thousands of tasks*** to keep track of across an entire workflow that can take ***~3 days to complete per sample seqenced***. These workflows usually feature a number steps that are executed on a ***'Per Sample Level'***, for example *Sequence Alignent, Downstream Read Processing, Variant Calling +/- Additional QC*. Which can then later be parallelized on the *Cohort Level* across the entire ***3 Billion Base Pairs of the Human Genome***

Adding another layer of complextity, is that fact the lists of all these various tasks are also highly *"Dynamic"* throughout a project, and largely temporary (deleted after completion). Where new samples can get sequenced / become available / drop out, or suffer some super magical technical blight during data processing, haulting their progression through the entire workflow. The cumulation of this means that one needs to be able *setup your 'ToDo' tasks in a simple manner*, and also be able to ***reliably query the workflow progress just as simply***. Which opens up the possibility in querying answers for common question like: *Which samples have been processed? How far along our workflow are we? How many samples are left to process? Which / How many samples are in step X, Y and / or Z?*



# Example

**1). Create some to do tasks and store in a DynamoDB Table**.

**2). Run PyAnamo to fetch all and process these tasks**.

**NB: The example assumes AWS and DynamoDB are setup for your account**.



## Create tasks


```
# Create table		<= Add to client
export PYANAMO=Path/to/where/git/was/downloaded
export PYANAMO_TABLE="Testing"
cd ${PYANAMO}
aws dynamodb create-table \
	--table-name "${PYANAMO_TABLE}" \
	--attribute-definitions AttributeName=itemID,AttributeType=N AttributeName=ItemState,AttributeType=S AttributeName=taskID,AttributeType=S AttributeName=InstanceID,AttributeType=S AttributeName=Log_Length,AttributeType=N \
	--key-schema AttributeName=itemID,KeyType=HASH \
	--provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 \
	--global-secondary-indexes file://${PYANAMO}/workflow-gsi-index.json


# Create some test tasks
for i in {1..16}
	do
	echo -e "Task-${i}|${PYANAMO_TABLE}|seq|${i},2,3"
done > ${PYANAMO_TABLE}-import.txt


# Import each of the 16 items as nested tasks: seq ${i}, seq 1, seq 2, seq 3
python import-items-generic.py -t ${PYANAMO_TABLE} -d ${PYANAMO_TABLE}-import.txt -s "|" -n ','


```


## Run PyAnamo


```
# Run pyanamo: Non-parallel
export PYANAMO=Path/to/where/git/was/downloaded
export PYANAMO_TABLE="My_Super_Fun_Happy_Table"
S3_BUCKET=SomeName
AWS_REGION=us-east-1
python pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}"



# Run pyanamo: Parallel N as options
python pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}" -i '2' -n '4'
```




