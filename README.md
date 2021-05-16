# PyAnamo


## Introduction
The purpose of *PyAnamo* is to automate "Big Data" *'Extraction Transformation and Loading'* procedures, ETLs, on AWS using Batch &amp; DynamoDB. The principal of operation is that each requested EC2 instance executes an application that iterates over a list of work to do, *tasks*, which are stored in a database. The database is populated with various collections of tasks that represent all of the work to do from your favourite workflow. Where each individual *collection* is a step of your workflow. The database can then be queried to monitor progress of each step of the workflow.

Each task for a given collection has a *"Task Script"* key whose value is executed by a *Generic PyAnamo Application*. The setup allows for each instance of the application, running across the cluster of size N, to iteratively execute *'Program A'* on all tasks in the collection of *'Workflow Step A'*. The application could also be potentially ported into existing setups at the users own discretion, ex 'https://doi.org/10.1093/bioinformatics/btz379'.

The **advantage** in storing all of the tasks in a database, specifically for ***Population Based Reseqeucning Studies***, is that there can be ***ten's of thousands of tasks*** to keep track of across an entire workflow that can take ***~3 days to complete per sample seqenced***. These workflows usually feature a number steps that are executed on a ***'Per Sample Level'***, for example *Sequence Alignent, Downstream Read Processing, Variant Calling +/- Additional QC*. Which can then later be parallelized on the *Cohort Level* across the entire ***3 Billion Base Pairs of the Human Genome***

Adding another layer of complextity, is that fact the lists of all these various tasks are also highly *"Dynamic"* throughout a project, and largely temporary (deleted after completion). Where new samples can get sequenced / become available / drop out, or suffer some super magical technical blight during data processing, haulting their progression through the entire workflow. The cumulation of this means that one needs to be able *setup your 'ToDo' tasks in a simple manner*, and also be able to ***reliably query the workflow progress just as simply***. Which opens up the possibility in querying answers for common question like: *Which samples have been processed? How far along our workflow are we? How many samples are left to process? Which / How many samples are in step X, Y and / or Z?*



# Example

**1). Running PyAnamo**.

**2). Creating PyAnamo Tasks**.

**NB: The example assumes AWS (IAM, ECR, Batch etc) and DynamoDB are setup for your account**.



## Run PyAnamo

The collective productivity for the cluster of PyAnamo batch computing jobs is: **N Jobs * N Parallel Item * N Parallel Nests**. Meaning that 1000 jobs, fetching 3 items and working on 4 nested tasks on each of those items can have productivity of **12,000** **tasks**, instead of *1000* with a *"1 job = 1 task workflow"*.


```bash
# Run pyanamo: Non-parallel
export PYANAMO=Path/to/where/git/was/downloaded
export PYANAMO_TABLE="My_Super_Fun_Happy_Table"
S3_BUCKET=SomeName
AWS_REGION=us-east-1
python pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}"


# Run pyanamo: Application process 2 items at time, and 4 nested tasks from the active item
python pyanamo.py -t "${PYANAMO_TABLE}" -i '2' -n '4' -b "${S3_BUCKET}" -r "${AWS_REGION}"
```



## Create Tasks

Examples of importing single / nested items from a file. The use of nested items should be dependant on the time taken for processing a collection of work per item (***i.e Spot Optimized***). For the use cases in this repo, simply calling variants per chromosome of individuals genome (***~2hrs***), instead the entirety in one go (***~50hrs***).

The use of the Super Mario Play Time Optimizer is purely conceptional to convey that the *deployment of ETLs can be broken up and grouped* into related work (*like chromosomes per persons genome*). Such as the hypothetical concept of optimizing the play times for Super Mario based on training on different levels and the different difficulties of those levels. 

The advantage of this is that PyAnamo can parallelize the implementation by Level across an entire cluster (*number of jobs*), within each instance (*single item parallelization*) and also the different difficulties of these levels (*nested task parallelization*).

```bash
# Write a list single items: Header and format is expected, delimiter optional
echo -e "
itemID|TaskID|TaskScript
Seq_Test_1|Task_1|seq 1
Seq_Test_2|Task_1|seq 2
Sample1_chr1-3|Sample1|bash use_cases/example_docker/HaplotypeCaller Sample1 chr1,chr2,chr3
Level_1_Time|Level_1|bash SuperMarioPlayTimeOptimizer.sh 1 Easy,Normal,Hard
Level_2_Time|Level_2|bash SuperMarioPlayTimeOptimizer.sh 2 Easy,Normal,Hard
" > import-testing.txt

# Import list of single items
python import-items.py 'Example_Table' 'us-east-1' 'import-testing.txt' '|'


# Write a list nested items to the same table: Delimiters optional
echo -e "
itemID|TaskID|TaskScript|TaskArgs
Seq_Tests|Seq_8_2_1|seq|8,2,1
Sample1|Sample1|bash use_cases/example_docker/HaplotypeCaller Sample_1|chr1,chr2,chr3
Level_1_Difficulty_Time|Level_1|bash SuperMarioPlayTimeOptimizer.sh 1|Easy,Normal,Hard
Level_2_Time|Level_2|bash SuperMarioPlayTimeOptimizer.sh 2 Easy,Normal,Hard
" > import-nested-testing.txt


# Import
python import-items.py 'Example_Table' 'us-east-1' 'import-nested-testing.txt' '|' ','
```



Storing the todo list in DynamoDB provides the user with a *database to centralize and query the progress of deploying their ETLs*, and in the case of nested tasks do more work per job. While also having the means to simply take-up the processing of the tasks in separate jobs if needs be (see ***Restarting PyAnamo Tasks*** in the "***Creating and Managing Workflows.md***"). Alongside the simple monitoring of the workflow as a whole, along with the simple means to view the progress of all nested tasks (see ***Monitoring Workflow** Progress* in the "***Creating and Managing Workflows.md***")
