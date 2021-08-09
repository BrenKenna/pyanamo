#!/bin/bash


########################################################################
########################################################################
#
# Install Minconda, PyAnamo and Reference Data
#
########################################################################
########################################################################


# Sanity check aws batch job definition job args
PATH="/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin:/usr/local/sbin"
export AWS_DEFAULT_REGION="us-east-1"
scriptsTar=$1
echo -e "\\n\\n\\nChecking Args, Node & Java Version\\n"
echo -e "Pyanamo Workflow Table = ${PYANAMO_TABLE}"
echo -e "PyAnamo Parallel Items = ${PYANAMO_ITEMS}"
echo -e "PyAnamo Parallel Nestes = ${PYANAMO_NESTS}"
echo -e "S3 Bucket = ${S3_BUCKET}"
echo -e "Pipeline Scripts = ${scriptsTar}"
df -h
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
# conda install -y -c conda-forge r-base=3.6 &>> /dev/null
# conda install -y -c r r-rpart r-dplyr r-ggplot2 r-rsqlite &>> /dev/null


# Install & complie software so its executable with all other Miniconda software
wget -q https://github.com/samtools/samtools/releases/download/1.11/samtools-1.11.tar.bz2
tar -xf samtools-1.11.tar.bz2
cd samtools-1.11
./configure --prefix=${TMPDIR}/software &>> /dev/null
make all all-htslib -j 2 &>> /dev/null
make install install-htslib &>> /dev/null
echo -e "\\n\\n\\nINSTALL HTSLIB COMPLETE\\n\\nChecking installaion\\n\n"


# Install PyAnamo
echo -e "\\nInstalling PyAnamo\\n"
cd ${TMPDIR}/software/bin
git clone --recursive https://github.com/BrenKenna/pyanamo.git
ls -lhd ${TMPDIR}/software/bin/*/
cd pyanamo
ls -lh *py
chmod +x code/*py
cp code/*py ${TMPDIR}/software/bin/
export PYANAMO=${TMPDIR}/software/bin/pyanamo/code
echo -e "PyAnamo Installed to ${PYANAMO}"


# Get the workflow task scripts etc: Stuff saved in a PyAnamo sub-folder
# These are the Task Scripts that PyAnamo will try to execute
echo -e "\\n\\nInstalling Pipeline Scripts\\n\\n\\n"
cd ${TMPDIR}/software/bin
aws s3 --quiet cp ${scriptsTar} ${TMPDIR}/software/bin/
tar -xf $(basename ${scriptsTar})
rm -f $(basename ${scriptsTar})
export PIPELINE=${TMPDIR}/software/bin/$(basename ${scriptsTar} | cut -d \. -f 1)
export PATH=${PATH}:${TMPDIR}/software/bin/$(basename ${scriptsTar} | cut -d \. -f 1)
echo -e "Pipeline Scripts Installed to = ${PIPELINE}"


########################################################################
########################################################################
#
# Handle AWS-Batch Table Name Argument
#
########################################################################
########################################################################


# Manage reference data to download
echo -e "\\n\\nFetching reference data\\n"
export wrk=${TMPDIR}/${PYANAMO_TABLE}
mkdir -p ${wrk}/ReferenceData && cd ${wrk}/ReferenceData
. ${PIPELINE}/job-conf.sh
aws s3 cp --quiet ${key} ${wrk}/ReferenceData/
if [ "${PYANAMO_TABLE}" == "TOPMed_Calling" ] || [ "${PYANAMO_TABLE}" == "KG_Testing" ]
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
	ls -lh ${ref} ${gatk}
	df -h
else
	echo -e "\\nError supplied table = ${PYANAMO_TABLE} not coverd"
fi


########################################################################
########################################################################
#
# Determine How to Execute PyAnamo
#
########################################################################
########################################################################


# Run without parallelization
echo -e "\\n\\nSetup complete. Executing application\\n"
cd $PYANAMO
if [ -z "${PYANAMO_ITEMS}" ] && [ -z "${PYANAMO_NESTS}" ]
then

	# Execute pyanamo single processing
	echo -e "\\n\\nRunning complete single item processing\\n"
	/usr/bin/time python ${PYANAMO}/pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}"


# Run with item parallelization
elif [ ! -z "${PYANAMO_ITEMS}" ] && [ -z "${PYANAMO_NESTS}" ]
then

	# Execute item parllelization
	echo -e "\\n\\nRunning item parallelization\\n"
	/usr/bin/time python ${PYANAMO}/pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}" -i "${PYANAMO_ITEMS}"


# Run with nested parallelization
elif [ ! -z "${PYANAMO_NESTS}" ] && [ -z "${PYANAMO_ITEMS}" ]
then

	# Execute item parllelization
	echo -e "\\n\\nRunning nested parallelization\\n"
	/usr/bin/time python ${PYANAMO}/pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}" -n "${PYANAMO_NESTS}"


# Run with both item and nested parallelization
elif [ ! -z "${PYANAMO_NESTS}" ] && [ ! -z "${PYANAMO_ITEMS}" ]
then

	# Execute item parllelization
	echo -e "\\n\\nRunning both single item and nested parallelization\\n"
	/usr/bin/time python ${PYANAMO}/pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}" -i "${PYANAMO_ITEMS}" -n "${PYANAMO_NESTS}"


# Otherwise try execute single processing
else

	# Execute pyanamo single processing
	echo -e "\\nUnable to handle the ${PYANAMO_ITEMS} and ${PYANAMO_NESTS} arguments, falling back to single items"
	/usr/bin/time python ${PYANAMO}/pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}"

fi
