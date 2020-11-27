# PyAnamo
The purpose of *PyAnamo* is to automate "Big Data" ETLs on AWS using EC2 &amp; DynamoDB. The principal of operation is that each requested EC2 instance executes an application that iterates over a list of work to do, *tasks*, which are stored in a database. The database is populated with various collections of tasks that represent all of the work to do from your favourite workflow. Where each individual *collection* is a step of your workflow. The database can then be queried to monitor progress of each step of the workflow.

In the **current PiCaS + couchDB setup**, each task for a given collection, has a *"Task Script"* key whose value is executed by a *Generic PiCaS Application*. The setup allows for each instatnce of the application, running across the cluster of size N, to iteratively execute *'Program A'* on all tasks in the collection of *'Workflow Step A'*. The application could also be potentially ported into existing setups at the users own discretion, ex 'https://doi.org/10.1093/bioinformatics/btz379'.

The **advantage** in storing all of the tasks in a database, specifically for ***Population Based Reseqeucning Studies***, is that there can be ***ten's of thousands of tasks*** to keep track of across an entire workflow that can take ***~3 days to complete per sample seqenced***. These workflows usually feature a number steps on executed on a ***'Per Sample Level'***, for example *Sequence Alignent, Downstream Read Processing, Variant Calling +/- Additional QC*. Which can then later be parallelized on the *Cohort Level* across the entire ***3 Billion Base Pairs of the Human Genome***..... Making even MORE work to keep track of :(.

Adding another layer of complextity, is that fact the lists of all these various tasks are also highly *"Dynamic"* throughout a project, and largely temporary (deleted after completion). Where new samples can get sequenced / become available / drop out, or suffer some super magical technical blight on the workflow level, that haults their progression through the entire workflow. The cumulation of this means that one needs to be able *setup your 'ToDo' tasks in a simple manner*, and also be able to ***reliably query the workflow progress just as simply***. Which opens up the possibility in querying answers for common question like: *Which samples have been processed? How far along our workflow are? How many samples are left to process? How many are in step X, Y and / or Z?* The database can also be used in conjunction with an SQL database which acts as an overall Content Management System *(this sample has this file path on S3, qc metrics etc)*.

The combination of a super simple **'Start a Cluster of HaplotypeCaller or Sequence Alignment Jobs'**, that will iterate over all the avaible work to do, coupled with our ability to query workflow status is why we have chosen our current AWS services + Setup.


# Example
The current tutorial developed from some *'Free Tier'* work on AWS, and our currently *very excited* to be porting this onto a **DynamoDB back-end** instead of couchDB backend *(overall principal is the same)*. The example consits of two steps:

**1). Create a to do task and store in DB**.

**2). Startup a pipeline step specific cluster**.

**NB: The example assumes AWS, DynamoDB and dbGaP authorization, alongside an AMI + an EC2 launch template (named by step in workflow)**.



## Create tokens

```python
view = "Testing"
taskScript = """sleep 5s"""
credentials.VIEW_NAME = view
db = couchdb.Database(credentials.URL + "/" + credentials.DBNAME)
db.resource.credentials = (credentials.USERNAME, credentials.PASS)

for i in range(0,9):
	tokenname = str( "SuperAwesome_Token_" + str(round(random() * 200)) + "_Testing")
	if tokenname in db:
		print("Skipping " + tokenname)
	else:
		token = {"_id": tokenname, "lock": 0, "done": 0, "type": view, "files": 'doggie', "Task_ID": tokenname, "Task_Script": taskScript}
		db.save(token)
```


## Execute application locally
```bash
python PiCaS-General.py ${VIEW_NAME}
```


## Start Cluster to Run the Pipeline
Run the below to start your cluster, note that by naming your EC2 launch template you can retrive the active instanceIDs *'Name'* within the *'User-Data Script'*. Which allows the script to know which pipeline to start ploughing through, meaning less scripts and code. The world is also your oyster for fail safes that you can add to prevent wasted hours on *EC2 Spot Instances*, ex *terminating the active instanceID* if the *application* that iterates over the DB *fails* or *does not have read/write permissions* to the pipelines results S3 directory. You can also set the *Njobs variable*, so that the *number of active EC2 instances < Number of tasks in workflow* step; X, Y, Z. And finally, you can also open out cluster monitoring on the instance level by storing the output of *'aws ec2 run-instances'* in text file or an *SQLite DB* if your super hardcore :).

```bash
aws ec2 run-instances --count ${Njobs} --user-data file://~/custom-pipeline/EC2-Fetch-Run.sh --launch-template "LaunchTemplateName=${Workflow}" > instance-data-${Njobs}.txt
```
