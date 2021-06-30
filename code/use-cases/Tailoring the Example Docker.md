# Tailoring the Example Docker

As per https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/ AWS Batch jobs start a docker container, which executes a script. The example_docker takes this "fetch-and-run.sh" / "***Pilot Job Script***" and uses it to install all software and reference data needed for the specific workflow table. Once complete, PyAnamo is then executed to process work to do from the supplied DynamoDB Table as shown in the below.

Since AWS Batch Job definitions can be created with input arguments and global variables, it is simplest to just create 1 compute environment per workflow table. In this example we have created a compute environment called "***HaplotypeCaller***" (the variant calling algorithm used), a job queue called "***HaplotypeCaller_Queue***" and a Job Definition called "***HaplotypeCaller_JobDef***". Before submitting jobs we will also create a PyAnamo / DynamoDB workflow table called "***HaplotypeCaller***".



## Docker 

Once the core software is installed the container will execute a custom "***Fetch and Run Script***". The job definition uses global variables for:

1.  PyAnamo Table which in this case is "***HaplotypeCaller***"  (PYANAMO_TABLE).

2. An S3 Bucket to put job related logs into if too big for DynamoDB or CloudWatch (S3_BUCKET).

3. Number of items to parallelize over (PYANAMO_ITEMS).

4. Number of nested tasks to parallelize over (PYANAMO_NESTS).

   

```dockerfile
FROM amazonlinux:latest

# Install core software
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

For the sake of managing multiple workflows users can store an archive of these "***Task Scripts***" on S3, or indeed bake into the docker container the same way as the "Fetch_and_Run.sh" is before the entry point ocurrs. In this repo an S3 archive is managed as is provided as an argument in the AWS Batch Job Definition.

The steps of the pilot job script are (see "***example_docker/Fetch_and_Run.sh***"):

1. ### **Installing software in an AWS Batch Job**

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
   
   # Set vars for installation
   export TMPDIR=/tmp/pipeline
   export wrk=${TMPDIR}
   export PATH="${wrk}/software/bin:$PATH"
   mkdir -p ${TMPDIR} && cd ${TMPDIR}
   
   # Install miniconda
   echo -e "\\n\\nInstalling Miniconda\\n\\n\\n"
   wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   chmod +x Miniconda3-latest-Linux-x86_64.sh
   ./Miniconda3-latest-Linux-x86_64.sh -u -b -p ${wrk}/software &>> /dev/null
   export CMAKE_PREFIX_PATH="${TMPDIR}/software"
   export PATH=${TMPDIR}/software/bin:$PATH
   conda install -y -c anaconda boto3 &>> /dev/null
   conda install -y -c conda-forge r-base=3.6 &>> /dev/null
   conda install -y -c r r-rpart r-dplyr r-ggplot2 r-rsqlite &>> /dev/null
   wget -q https://github.com/samtools/samtools/releases/download/1.11/samtools-1.11.tar.bz2
   tar -xf samtools-1.11.tar.bz2
   cd samtools-1.11
   ./configure --prefix=${wrk}/software &>> /dev/null
   make all all-htslib -j 2 &>> /dev/null
   make install install-htslib &>> /dev/null
   echo -e "\\n\\n\\nINSTALL HTSLIB COMPLETE\\n\\nChecking installaion\\n\n"
   
   # Get workflow task scripts etc: Stuff saved in a PyAnamo sub-folder
   # These are the Task Scripts that PyAnamo will try to execute
   echo -e "\\n\\nInstalling PyAnamo\\n\\n\\n"
   cd ${wrk}/software/bin
   aws s3 --quiet cp ${scriptsTar} ${wrk}/software/bin/
   tar -xf $(basename ${scriptsTar})
   rm -f $(basename ${scriptsTar})
   # export PYANAMO=${wrk}/software/bin/PyAnamo
   export PATH=${wrk}/software/bin/PyAnamo
   # echo -e "PyAnamo Path = ${PYANAMO}"
   ```

2. ### **Fetching Workflow Table Specific Data / Software**

```bash
# Load the variables as in "example_docker/job-conf.sh"
# This defines variables described in the Task Scripts
# and variables such gatk4, ref, refInd below
. ${PYANAMO}/job-conf.sh
aws s3 cp --quiet ${key} ${wrk}/ReferenceData/
export key=${wrk}/ReferenceData/prj_16444.ngc
if [ "${PYANAMO_TABLE}" == "HaplotypeCaller" ]
	then

	# Download HaplotypeCaller Software & Data
	echo -e "\\nDownloading reference data for HaplotypeCaller\\n"
	aws s3 cp --quiet ${gatk4} ${wrk}/ReferenceData/
	aws s3 cp --quiet ${ref} ${wrk}/ReferenceData/
	aws s3 cp --quiet ${refInd} ${wrk}/ReferenceData/
	aws s3 cp --quiet ${refDic} ${wrk}/ReferenceData/
	aws s3 cp --quiet ${tgt} ${wrk}/ReferenceData/
	export ref=${wrk}/ReferenceData/hs38DH.fa
	export gatk4=${wrk}/ReferenceData/gatk-package-4.1.4.0-local.jar
	export tgt=${wrk}/ReferenceData/cds_100bpSplice_utr_codon_mirbase.bed
else
	echo -e "\\nError supplied table = ${PYANAMO_TABLE} not coverd"
fi
```

3. ### ***Running PyAnamo within an AWS Batch job***

```bash
# Install PyAnamo
cd ${wrk}/software/bin
git clone --recursive https://github.com/BrenKenna/pyanamo.git
cd pyanamo
chmod +x code/*py
cp code/*py ${wrk}/software/bin/
cd .. && rm -fr code/

# Execute pyanamo
python pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}"
```



## PyAnamo Task Scripts

PyAnamo uses a standardized schema so that users can run a specific wrapper script with their required arguments. In the example HaplotypeCaller.sh script this running a Variant Calling ETL over data from the 1 Thousand Genomes (1KG) because it is publicly available. Additionally these task script could be anything such as transferring data in/out of cloud.

For this variant calling ETL to work on AWS Batch we need to extract / download sequencing data from the 1KG S3 bucket, Transform / call variants over this data and then Load / copy the results to an S3 bucket. Our only argument for such an ETL is a sample to a process, and a region of the genome.

So before submitting job we should run the above installation and try executing the below task script.

```bash
# Locallly test execute the variant calling ETL over some sample from the 1KG bucket
bash HaplotypeCaller-1KG.sh ${SOME_SAMPLE} ${SOME_LOCI}
```



## Summary

This page covers all of the core background for running PyAnamo in AWS Batch jobs by hijacking through https://aws.amazon.com/blogs/compute/creating-a-simple-fetch-and-run-aws-batch-job/. With the workflow specific AWS Batch Compute Environment and ETL / Task Script and Docker + Generic Pilot Job Script debugged & in place, we can now host the todo list on DynamoDB and submit jobs to do all the work ("***Submitting Use Case Variant Calling Jobs.md***").
