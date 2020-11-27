# PyAnamo
Automate "Big Data" ETLs on AWS using EC2 &amp; DynamoDB (After swapping out couchDB in favor of it of course ;) ). The principal is that each requested EC2 instance, executes an application that iterates over a list of work to do that is stored in a database. The database contains collection of items that represent all the work to do from your favourite workflow. With our **current PiCaS + couchDB setup**, each item in our collection of work to do, has a *"Task Script"* key which is executed by a generic PiCaS application. The setup allows for each instatnce of the application that is running across cluster of size N, will iteratively execute *'Program A'* on all items in the collection of *'Workflow Step A'*.

The **advantage** in storing all the various todo work in a database (ie RMDBS / NoSQL), specifically for **Population Based Reseqeucning Studies**, is that there can be **ten's of thousands of tasks** to keep track of across an entire workflow that can take *>56hrs to complete per sample seqenced*. These workflows usually a number steps on the *'Per Sample Level'* (*Sequence Alignent, Downstream Read Processing, Variant Calling +/- Additional QC*), which can then later be parallelized across the entire *3 Billion Base Pairs of the Human Genome*..... Making even MORE work to keep track of :'(.

Adding another layer of complextity is that fact these lists of various tasks to do are also highly *"Dynamic"*, as new samples can get sequenced / become available / drop out, or suffer some super magical technical blight that haults their progression through the workflow. The cumulation of all this means that you need to be able *setup your 'to do' tasks in a simple manner*, and also be able to *reliably query the workflow progress as simply*. Which opens up the simplicity in querying answers for common question like: *Which samples have been processed? How far along our workflow are? How many samples are left to process? How many are in step X, Y and / or Z?* The database can also be used in conjunction with an RMDBS supported by SQLite which acts as an overall Content Management System, but that's for laterz ;)!

The combination of a super simple **'Start a Cluster of HaplotypeCaller or Sequence Alignment Jobs'**, that will iterate over all the avaible work to do, coupled with our ability to query workflow status is why we have chosen our current AWS services + Setup.


# Examples
The current tutorial is a port of our *'Free Tier'* allocation work on AWS, and our currently *very excited* to be porting this onto a **DynamoDB back-end** instead of couchDB backend (overall principal is the same). The example consits of two steps:

**1). Create a to do task and store in DB.
2). Startup a pipeline step specific cluster.
3). Treat yourself to a coffee and chocolate muffin :)
**
** NB: The example assumes; AWS, DynamoDB and dbGaP authorization, alongside an AMI + an EC2 launch template (named by step in workflow).**


## Create tokens

```python
view = "Testing"
taskScript = """sleep 5s"""
credentials.VIEW_NAME = view
db = couchdb.Database(credentials.URL + "/" + credentials.DBNAME)
db.resource.credentials = (credentials.USERNAME, credentials.PASS)

for i in range(0,90):
	tokenname = str( "SuperAwesome_Token_" + str(round(random() * 200)) + "_Testing")
	if tokenname in db:
		print("Skipping " + tokenname)
	else:
		token = {"_id": tokenname, "lock": 0, "done": 0, "type": view, "files": 'doggie', "Task_ID": tokenname, "Task_Script": taskScript}
		db.save(token)
```

## Start Cluster & Run Pipeline
Run the below to start your cluster, note that by naming your EC2 launch template you can retrive the active instanceIDs *'Name'* within the *'User-Data Script'*. Which allow the script to know which pipeline to start plough through, meaning less scripts and code. The world is also your oyster for fail safes that you add to prevent waste, ex terminating the active instanceID if the application that iterates over the DB fails. You can also set the Njobs variable, so that the number of active EC2 instances will never be greater than the number of tasks in workflow step; X, Y, Z. And finally, you can also open out cluster monitoring on the instance level by storing the output of *'aws ec2 run-instances'* in text file or an *SQLite DB* if your super hardcore :).

```bash
aws ec2 run-instances --count ${Njobs} --user-data file://~/custom-pipeline/EC2-Fetch-Run.sh --launch-template "LaunchTemplateName=${Workflow}" > instance-data-${Njobs}.txt
```
