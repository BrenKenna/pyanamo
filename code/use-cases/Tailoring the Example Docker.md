# Tailoring the Example Docker

As per https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/ AWS Batch jobs start a docker container, which executes a script. The example_docker takes this "fetch-and-run.sh" / "***Pilot Job Script***" and uses it to install all software and reference data needed for the specific workflow table. Once complete, PyAnamo is then executed to process work to do from the supplied DynamoDB Table as shown in the below.

Since AWS Batch Job definitions can be created with input arguments and global variables, it is simplest to just create 1 compute environment per workflow table. In this example we have created a compute environment called "***HaplotypeCaller***" (the variant calling algorithm used), a job queue called "***HaplotypeCaller_Queue***" and a Job Definition called "***HaplotypeCaller_JobDef***". Before submitting jobs we will also create a PyAnamo / DynamoDB workflow table called "***HaplotypeCaller***".



## Workflow Docker 

Once the core software is installed the container will execute a custom "***Fetch and Run Script***" which will install any software / reference data that your workflow needs before running PyAnamo.

```dockerfile
FROM amazonlinux:latest

# Install core software
# Could install something miniconda here, but intentionally saving for the job script
RUN yum -y update && \
        yum install -y unzip which ls bash du df aws-cli tar time chmod \ 
        	ncurses-compat-libs.x86_64 hostname ncurses-c++-libs.x86_64 \ 
        	ncurses.x86_64 ncurses-devel.x86_64 ncurses-libs.x86_64 gcc \ 
        	autoconf automake make gcc perl-Data-Dumper zlib-devel bzip2 \ 
        	bzip2-devel xz-devel curl-devel openssl-devel ncurses-devel java-1.8.0-openjdk wget curl


# Run job script
WORKDIR /tmp
ADD Fetch_and_Run.sh /usr/local/bin/Fetch_and_Run.sh
USER nobody
ENTRYPOINT ["/usr/local/bin/Fetch_and_Run.sh"]
```



## Generic Fetch and Run / Pilot Job Script

In order to manage different workflows AWS Batch Job Definition should use global variables for:

1. The PyAnamo Table which in this case is "***HaplotypeCaller***"  (PYANAMO_TABLE).
2. An S3 Bucket to put job related logs into if too big for DynamoDB or CloudWatch (S3_BUCKET).
3. Number of items to parallelize over (PYANAMO_ITEMS).
4. Number of nested tasks to parallelize over (PYANAMO_NESTS).

For the sake of managing multiple workflows users can store an archive of these "***Task Scripts***" on S3, or indeed bake them into the docker container the same way as the "Fetch_and_Run.sh" is before the entry point occurs. In this repo an S3 archive is managed and is provided as an argument in the AWS Batch Job Definition.

The steps of the pilot job script are outlined below (see "***example_docker/Fetch_and_Run.sh***" for the specific pilot job script):

### **i). Installing software in an AWS Batch Job**

```bash
# Sanity check aws batch job definition job args
PATH="/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin:/usr/local/sbin"
export AWS_DEFAULT_REGION="us-east-1"
scriptsTar=$1
echo -e "\\n\\n\\nChecking Args, Node & Java Version\\n"
echo -e "Pyanamo Workflow Table = ${PYANAMO_TABLE}"
echo -e "PyAnamo Parallel Items = ${PYANAMO_ITEMS}"
echo -e "PyAnamo Parallel Nestes = ${PYANAMO_NESTS}"
echo -e "S3 Bucket = ${S3_BUCKET}"
echo -e "\\nChecks Complete\\n\\nInstalling software\\n"


# Install miniconda
echo -e "\\n\\nInstalling Miniconda\\n\\n\\n"
export TMPDIR=/tmp/pipeline
mkdir -p ${TMPDIR} && cd ${TMPDIR}
wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh -u -b -p ${TMPDIR}/software &>> /dev/null
export CMAKE_PREFIX_PATH="${TMPDIR}/software"
export PATH=${TMPDIR}/software/bin:$PATH
conda install -y -c anaconda boto3 &>> /dev/null
conda install -y -c conda-forge r-base=3.6 &>> /dev/null
conda install -y -c r r-rpart r-dplyr r-ggplot2 r-rsqlite &>> /dev/null

# Install & complie software so its executable with all other Miniconda software
wget -q https://github.com/samtools/samtools/releases/download/1.11/samtools-1.11.tar.bz2
tar -xf samtools-1.11.tar.bz2
cd samtools-1.11
./configure --prefix=${TMPDIR}/software &>> /dev/null
make all all-htslib -j 2 &>> /dev/null
make install install-htslib &>> /dev/null
echo -e "\\n\\n\\nINSTALL HTSLIB COMPLETE\\n\\nChecking installaion\\n\n"

# Get the workflow task scripts etc: Stuff saved in a PyAnamo sub-folder
# These are the Task Scripts that PyAnamo will try to execute
echo -e "\\n\\nInstalling PyAnamo\\n\\n\\n"
cd ${TMPDIR}/software/bin
aws s3 --quiet cp ${scriptsTar} ${TMPDIR}/software/bin/
tar -xf $(basename ${scriptsTar})
rm -f $(basename ${scriptsTar})
# export PYANAMO=${wrk}/software/bin/PyAnamo
export PATH=${TMPDIR}/software/bin/PyAnamo
# echo -e "PyAnamo Path = ${PYANAMO}"
```



### **ii). Fetching Workflow Table Specific Data / Software**

```bash
# Load the variables as in "example_docker/job-conf.sh"
# This defines variables described in the Task Scripts
# and variables such gatk4, ref, refInd below
. ${PYANAMO}/job-conf.sh
aws s3 cp --quiet ${key} ${TMPDIR}/ReferenceData/
if [ "${PYANAMO_TABLE}" == "HaplotypeCaller" ]
	then

	# Download HaplotypeCaller Software & Data
	echo -e "\\nDownloading reference data for HaplotypeCaller\\n"
	aws s3 cp --quiet ${gatk4} ${TMPDIR}/ReferenceData/
	aws s3 cp --quiet ${ref} ${TMPDIR}/ReferenceData/
	aws s3 cp --quiet ${refInd} ${TMPDIR}/ReferenceData/
	aws s3 cp --quiet ${refDic} ${TMPDIR}/ReferenceData/
	aws s3 cp --quiet ${tgt} ${TMPDIR}/ReferenceData/
	export ref=${TMPDIR}/ReferenceData/hs38DH.fa
	export gatk4=${TMPDIR}/ReferenceData/gatk-package-4.1.4.0-local.jar
	export tgt=${TMPDIR}/ReferenceData/cds_100bpSplice_utr_codon_mirbase.bed
else
	echo -e "\\nError supplied table = ${PYANAMO_TABLE} not coverd"
fi
```

### iii). Running PyAnamo within AWS batch jobs

```bash
# Install PyAnamo
cd ${TMPDIR}/software/bin
git clone --recursive https://github.com/BrenKenna/pyanamo.git
cd pyanamo
chmod +x code/*py
cp code/*py ${TMPDIR}/software/bin/
cd .. && rm -fr code/

# Execute pyanamo
python pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}"
```



## PyAnamo Task Scripts

PyAnamo uses a standardized schema so that users can run a specific wrapper script with their required arguments. The example "*HaplotypeCaller-KG.sh*" script is running a "*Variant Calling*" ETL over data from the *Thousand Genomes* (1KG) because it is publicly available sequencing data. Additionally these task scripts could be anything such as transferring data in/out of cloud, downloading websites then checking their sizes etc.

For this variant calling ETL to work on AWS Batch we need to 

i). *Extract* i.e download sequencing data from the 1KG S3 bucket onto the active container.

ii). *Transform* i.e call variants over this data.

iii). *Load* i.e copy the results to an S3 bucket.

Our only argument for such an ETL is then a sample to a process, and a region of the genome (for super duper parallelization).

So before submitting job we should **<u>*run the above installation and list 10 random samples from the 1KG*</u>** so that we test our ETL locally before scaling out our deployment.

```bash
# List some data from the 1KG Pubic S3 Bucket
aws s3 ls s3://1000genomes/1000G_2504_high_coverage/data/ | sort -R | head | sed 's/\///g' | awk '{print $NF}' > 1KG-Data.txt
```

With our reference data + software locally installed and our of list of to do items, we can now simulate what PyAnamo is going to do with our task script, specifically for two random genes.

```bash
# Simulate PyAnamo exectuing the task script for the SOD1 and NEK1 genes
locis="chr21:31659566-31669931,chr4:169391809-169613627"
for sampleID in $(cat 1KG-Data.txt)

	# Locallly test execute the variant calling ETL over some sample from the 1KG bucket
	bash HaplotypeCaller-1KG.sh ${sampleID} ${locis}

done
```

With this we're now all set for scaling out the deployment of our Big Data ETL as per "***Submitting Use Case Variant Calling Jobs.md***"

## Summary

This page covers all of the core background for running PyAnamo in AWS Batch jobs by hijacking through https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/. With the workflow specific AWS Batch Compute Environment and ETL / Task Script and Docker + Generic Pilot Job Script debugged & in place, we can now host the to do list on DynamoDB and submit jobs to do all the work ("***Submitting Use Case Variant Calling Jobs.md***").
