FROM amazonlinux:latest

# Install core software
RUN yum -y update && \
        yum install -y git unzip which ls bash du df aws-cli tar time chmod jq ncurses-compat-libs.x86_64 hostname ncurses-c++-libs.x86_64 ncurses.x86_64 ncurses-devel.x86_64 ncurses-libs.x86_64 gcc autoconf automake make gcc perl-Data-Dumper zlib-devel bzip2 bzip2-devel xz-devel curl-devel openssl-devel ncurses-devel java-1.8.0-openjdk wget curl


# Run job script
WORKDIR /tmp
ADD Fetch_and_Run.sh /usr/local/bin/Fetch_and_Run.sh
USER nobody
ENTRYPOINT ["/usr/local/bin/Fetch_and_Run.sh"]
