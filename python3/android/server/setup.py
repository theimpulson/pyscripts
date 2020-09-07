#!/usr/bin/python3
# Copyright 2020 Aayush Gupta
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import paramiko

from os.path import expanduser

userinfo = [
    'Aayush Gupta',
    'theimpulson',
    'aayushgupta219@gmail.com'
]

parser = argparse.ArgumentParser(description='python3 script to setup a remote server for android building purposes')
parser.add_argument('-u', '--user', type=str, help='User to login into the remote server')
parser.add_argument('-addr', '--address', type=str, help='IP/Domain address of the remote server')
parser.add_argument('-pn', '--packet_nvme', type=bool, help='Bool to automatically create a nvme partition in packet server')
args = parser.parse_args()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

with open(expanduser('~/.ssh/id_rsa.pub')) as file:
    pub_key = file.read()

packages = "adb autoconf automake axel bc bison build-essential ccache clang cmake expat fastboot flex g++ git parted npm "\
           "g++-multilib gawk gcc gcc-multilib git gnupg gperf htop imagemagick lib32ncurses5-dev lib32z1-dev libtinfo5 libc6-dev libcap-dev "\
           "libexpat1-dev libgmp-dev '^liblz4-.*' '^liblzma.*' libmpc-dev libmpfr-dev libncurses5-dev libsdl1.2-dev libssl-dev libtool libxml2 "\
           "libxml2-utils '^lzma.*' lzop maven ncftp ncurses-dev patch patchelf pkg-config pngcrush pngquant python2.7 python-all-dev re2c "\
           "schedtool squashfs-tools subversion texinfo unzip w3m xsltproc zip zlib1g-dev lzip libxml-simple-perl apt-utils python"

bash_rc = r"""
# ccache (enable by default)
export USE_CCACHE=1
export CCACHE_EXEC='/usr/bin/ccache'

# tmux (UTF-8 support by default)
alias tmux='tmux -u'

# wget (disable certificate check by default)
alias wget='wget --content-disposition --no-check-certificate'

# nano (line numbers by default)
alias nano='nano -l'

# change dir
if [ -d '/nvme' ]; then
  cd /nvme
fi
"""

commands = [
    'sudo add-apt-repository universe && sudo apt update',
    f'sudo apt install {packages} -y',
    fr'echo "{userinfo[1]} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers',
    f'useradd -m {userinfo[1]} && usermod -aG sudo {userinfo[1]}',
    fr'chsh -s /bin/bash {userinfo[1]}',
    fr'touch /home/{userinfo[1]}/.cloud-warnings.skip',
    fr'mkdir -p /home/{userinfo[1]}/.ssh/',
    fr'echo "{pub_key}" > /home/{userinfo[1]}/.ssh/authorized_keys',
    f'git config --global user.email {userinfo[2]}',
    f'git config --global user.name {userinfo[0]}',
    'ccache -M 100G',
    f'echo "{bash_rc}" >> /home/{userinfo[1]}/.bashrc',
]

nvme = [
    r'mkfs.ext4 /dev/nvme0n1',
    r'mkdir -p /nvme && mount /dev/nvme0n1 /nvme',
    r'echo "/dev/nvme0n1     /nvme      ext4    errors=remount-ro    0    1"  >> /etc/fstab',
    fr'chown -R {userinfo[1]}:{userinfo[1]} /nvme',
]

# Connect to the given client
client.connect(args.address, username=args.user)
print('\033[92mConnection established!\033[00m')

# Execute the commands
print('\033[92mSetting up the server as required\033[00m\n')
for cmd in commands:
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    stdin.close()
    for line in iter(stdout.readline, ''):
        print(line, end='')
    for line in iter(stderr.readline, ''):
        print(line, end='')

if args.packet_nvme:
    print('\n\033[92mCreating & mounting nvme partition at /nvme\033[00m\n')
    for cmds in nvme:
        stdin, stdout, stderr = client.exec_command(cmds)
        stdin.close()
        for lines in stdout.readlines():
            print(lines.strip())
        for lines in stderr.readlines():
            print(lines.strip())

# Close the client as setup is done
client.close()
print('\n\033[92mSetup done!\033[00m')
