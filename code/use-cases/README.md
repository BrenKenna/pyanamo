
# Running PyAnamo in AWS-Batch jobs
This part of documentation is beginners guide to scaling the deployment of Big Data ETLs using PyAnamo within AWS Batch Job. The guide extends the AWS-Batch "Simple Fetch and Run" tutorial https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/, where that tutorial  + it's reference to the ***AWS Batch Wizard*** covers all of the basics of how to get started with AWS Batch. 

A verbose developer mode guide for how to tailor the "***example_docker***" for your own pipeline is provided in the "***Tailoring the Example Docker.md***". The document covers getting an ***AWS Batch Job Definition*** to run a generic job script that executes PyAnamo to fetch work to do for the definitions associated DynamoDB table. 

Once both of the above are complete you can look to the "***Submitting Use Case Variant Calling Jobs.md***" for an example of how to streamline a ***Big ETL on AWS Batch using PyAnamo***.

# 

PyAnamo in it's simplest form can always be executed by importing items and executing PyAnamo over the supplied table as per the below

```bash
# Write a list nested items to the same table: Delimiters optional
echo -e "
itemID|TaskID|TaskScript|TaskArgs
Seq_Test_1|Seq_8_2_1|seq|8,2,1
Seq_Test_2|Seq_4_5_3|seq|4,5,3
Seq_Test_3|Seq_6_7_9|seq|6,7,9
Seq_Test_4|Seq_5_8_2|seq|5,8,2
" > import-nested-testing.txt

# Import
python import-items.py 'Testing' 'us-east-1' 'import-nested-testing.txt' '|' ','

# Run PyAnamo to process the above to do items
python pyanamo.py -t "Testing" -b "${S3_BUCKET}" -r "${AWS_REGION}"
```

