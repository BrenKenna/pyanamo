# Set S3 paths
bucket=s3://My_S3_Bucket
project=${bucket}/projects
resources=${bucket}/reference_resources


# Results directories
bam=${project}/bam
gvcf=${project}/gvcf
ancestry=${project}/ancestry


# Pre-compiled software
gatk4=${resources}/gatk-package-4.1.4.0-local.jar
LASER=${resources}/LASER-2.04.tar.gz
laserMD5="1070b684a092f375516ab554671e36da"
kg_data=${resources}/GRCh38-1KG-Ancestry.tar.gz
kg_dataMD5="8dab78d9dafe1acff879d09a3d186b41"
key=${resources}/mydbGaP-repokey-lol.ngc
ref=${resources}/hs38DH.fa
refInd=${resources}/hs38DH.fa.fai
refDic=${resources}/hs38DH.dict
tgt=${resources}/cds_100bpSplice_utr_codon_mirbase.bed
