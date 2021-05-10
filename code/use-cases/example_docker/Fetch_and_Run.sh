#!/bin/bash


########################################################################
########################################################################
#
# Install Minconda, PyAnamo and Reference Data
#
########################################################################
########################################################################


# Parse input args
PATH="/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin:/usr/local/sbin"
export AWS_DEFAULT_REGION="us-east-1"
scriptsTar=$1
echo -e "\\n\\n\\nChecking Args, Node & Java Version\\n"
echo -e "${PYANAMO_TABLE}"
df -h
java -version
echo -e "\\nChecks Complete\\n\\n"


# Set vars for installation
export TMPDIR=/tmp/pipeline
export wrk=${TMPDIR}
export PATH="${wrk}/software/bin:$PATH"
rm -fr ${TMPDIR}
mkdir -p ${TMPDIR} && cd ${TMPDIR}
export CMAKE_PREFIX_PATH="${TMPDIR}/software"
export PATH=${TMPDIR}/software/bin:$PATH


# Install miniconda
echo -e "\\n\\nInstalling Miniconda\\n\\n\\n"
wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh -u -b -p ${wrk}/software &>> /dev/null
export CMAKE_PREFIX_PATH="${wrk}/software"
export PATH="${wrk}/software/bin:$PATH"
export PYTHONPATH="${wrk}/software/bin:${wrk}/software/pkgs"


# Install boto3, tabix and bcftools
# conda config --add channels bioconda
conda install -y -c anaconda boto3 &>> /dev/null
conda install -y -c conda-forge r-base=3.6 &>> /dev/null
conda install -y -c r r-rpart r-dplyr r-ggplot2 r-rsqlite &>> /dev/null
echo -e "\\n\\n\\nInstallation complete\\n\\nChecking installaion\\n\n"
which python R Rscript
python --version


# Install htslib 1.11
echo -e "\\n\\n\\nINSTALL HTSLIB\\n\\n"
wget -q https://github.com/samtools/samtools/releases/download/1.11/samtools-1.11.tar.bz2
tar -xf samtools-1.11.tar.bz2
cd samtools-1.11
./configure --prefix=${wrk}/software &>> /dev/null
make all all-htslib -j 2 &>> /dev/null
make install install-htslib &>> /dev/null
echo -e "\\n\\n\\nINSTALL HTSLIB COMPLETE\\n\\nChecking installaion\\n\n"
which samtools tabix bgzip


# Install PyAnamo
echo -e "\\n\\nInstalling PyAnamo\\n\\n\\n"
cd ${wrk}/software/bin
aws s3 --quiet cp ${scriptsTar} ${wrk}/software/bin/
tar -xf PyAnamo.tar.gz
rm -f PyAnamo.tar.gz
cp PyAnamo/* ./
export PYANAMO=${wrk}/software/bin/PyAnamo
echo -e "PyAnamo Path = ${PYANAMO}"


# 
# Install parallel
# cd ${wrk}/software/bin
# wget -q https://ftp.gnu.org/gnu/parallel/parallel-20120722.tar.bz2
# tar -xf parallel-20120722.tar.bz2
# rm -f parallel-20120722.tar.bz2
# cp parallel-20120722/src/* ./
# which parallel
#


# Setup task directory
echo -e "\\n\\nVerifying installation\\n"
which samtools tabix bgzip python R
samtools --version
echo -e "\\n\\nVerifying complete\\n"


########################################################################
########################################################################
#
# Handle AWS-Batch Table Name Argument
#
########################################################################
########################################################################


# Manage reference data to download
echo -e "\\n\\nFetching reference data\\n"
mkdir -p ${wrk}/ReferenceData && cd ${wrk}/ReferenceData
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


# Otherwise download ancestry references
elif [ "${PYANAMO_TABLE}" == "Ancestry" ]
	then

	# Download Ancestry Software & Data
	echo -e "\\nDownloading reference data for Ancestry\\n"
	aws s3 cp --quiet ${LASER} ${wrk}/ReferenceData/
	aws s3 cp --quiet ${kg_data} ${wrk}/ReferenceData/
	export LASER=${wrk}/ReferenceData/LASER-2.04
	export kgLoci=${wrk}/tgt.bed

	# Unpack
	tar -xf ${LASER}.tar.gz && rm -f ${LASER}.tar.gz
	tar -xf ${wrk}/ReferenceData/GRCh38-1KG-Ancestry.tar.gz && rm -f GRCh38-1KG-Ancestry.tar.gz
	export ref_site=${wrk}/ReferenceData/1KG-GRCh38-ALL-CommonQC.site
	export ref_geno=${wrk}/ReferenceData/1KG-GRCh38-ALL-CommonQC.geno
	export ref_coord=${wrk}/ReferenceData/1KG-GRCh38-ALL-CommonQC.RefPC.coord


# Otherwise exit
else
	echo -e "\\nNo reference data assigned to table = ${PYANAMO_TABLE}\\n"
	# exit

fi
echo -e "\\nDownloading and assigment complete. Verifying:\\n"
ls -lh ${key} ${wrk}/ReferenceData/



# Check reference / software disk usage
echo -e "\\n\\nChecking remaining storage after setup\\n"
df -h



########################################################################
########################################################################
#
# Run PyAnamo
#
########################################################################
########################################################################


# Execute task
echo -e "\\n\\nSetup complete. Executing application\\n"
/usr/bin/time -v python pyanamo.py -t "${PYANAMO_TABLE}" -b "${S3_BUCKET}" -r "${AWS_REGION}" -i '2' -n '4'
