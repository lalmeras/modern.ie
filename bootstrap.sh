#! /bin/bash

##
## This must be sourced: source bootstrap.sh
##

DEB_PACKAGES="python-virtualenv libssl-dev python-dev gcc libxml2-dev python-lxml libffi-dev"
RPM_PACKAGES="python2-virtualenv openssl-devel python-devel gcc libxml2-devel python-lxml libffi-devel"

echo -e "** Init and update submodules"
git submodule update --init --recursive

echo -e "** check packages installation"
if [ -f /usr/bin/apt-get ]; then
	sudo apt-get install $DEB_PACKAGES
elif [ -f /usr/bin/dnf ]; then
	sudo dnf install $RPM_PACKAGES
elif [ -f /usr/bin/yum ]; then
	sudo yum install $RPM_PACKAGES
fi

echo -e "** Create virtualenv"
tools_dir=.tools
mkdir -p "${tools_dir}"
rm -rf "${tools_dir}/click"
virtualenv "${tools_dir}/click"

source "${tools_dir}/click/bin/activate"
pip install "clickable >= 0.1.1"
pip install "invoke"

echo -e "** Bootstrap done"
echo -e "** Launch ./tasks.py --help to list available commands"
invoke --list

