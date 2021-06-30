
# Running PyAnamo in AWS-Batch jobs
Follows the AWS-Batch "Simple Fetch and Run" tutorial https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/. The tutorial  + it's reference to the ***AWS Batch Wizard*** covers all of the basics of how to get started with AWS Batch. 

A verbose guide for how to tailor the "***example_docker***" for your own pipeline is provided in the "***Tailoring the Example Docker.md***". The document covers getting an ***AWS Batch Job Definition*** to run a generic job script that executes PyAnamo to fetch work to do for the definitions associated DynamoDB table. 

Once both of the above are complete you can look to the "***Submitting Use Case Variant Calling Jobs.md***" for an example of how to streamline a ***Big ETL on AWS Batch using PyAnamo***.
