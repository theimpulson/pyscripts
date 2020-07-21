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

import subprocess

from shutil import copy, make_archive, rmtree
from os import environ, makedirs, path, remove
from datetime import datetime

# Device-specific variables
kernel_name = 'FireKernel'
version = 'r2.5'
device = 'NOKIA_SDM660'
zip_name = f"{kernel_name}-{version}-{datetime.today().strftime('%Y-%m-%d-%H-%M')}-{device}"
defconfig = 'nokia_defconfig'

# Required paths
kernel_dir = path.abspath('.')
ak_dir = f'{kernel_dir}/AnyKernel3'
img = f'{kernel_dir}/output/arch/arm64/boot/Image.gz-dtb'
upload_dir = path.abspath(f'{kernel_dir}/../{device}')

# Environment variables used by compiler
environ['PATH'] = path.abspath(f'{kernel_dir}/../proton-clang/bin:') + environ['PATH']
environ['ARCH'] = 'arm64'
environ['CROSS_COMPILE'] = 'aarch64-linux-gnu-'
environ['CROSS_COMPILE_ARM32'] = 'arm-linux-gnueabi-'


def make_kernel():
    """Creates defconfig as per given variable and compiles the kernel"""
    print(f"\033[96m{'*' * 10}Initializing defconfig{'*' * 10}\033[00m")
    subprocess.run([f'make {defconfig} CC=clang O=output/'], shell=True)
    print(f"\033[96m{'*' * 10}Building kernel{'*' * 10}\033[00m")
    process = subprocess.Popen(['make -j$(nproc --all) CC=clang O=output/'], shell=True)
    process.communicate()
    if process.returncode != 0:
        raise Exception('\033[91mKernel Compilation failed! Fix the errors!\033[00m')


def make_zip():
    """Creates a 'zip' archive from the given AnyKernel directory"""
    print(f"\033[96m{'*' * 10}Creating TWRP flashable zip!{'*' * 10}\033[00m")
    copy(img, ak_dir)
    makedirs(f'{upload_dir}', exist_ok=True)
    make_archive(f'{upload_dir}/{zip_name}', 'zip', f'{ak_dir}')
    print(f'Successfully created zip at {upload_dir}/{zip_name}.zip')


def cleanup(pre=False, post=False):
    """
    :pre: 'False' by default, removes existing output directory if 'True'
    :post: 'False' by default, removes kernel image from the AnyKernel directory if 'True'
    """
    if pre:
        print(f"\033[96m{'*' * 10}Removing existing output directory{'*' * 10}\033[00m")
        rmtree(f'{kernel_dir}/output')
    if post:
        print(f"\033[96m{'*' * 10}Cleaning up!{'*' * 10}\033[00m")
        remove(f'{ak_dir}/Image.gz-dtb')


def build():
    """Takes input from the user and starts the build"""
    build_type = input('Select one of the following types of build : \n1.Dirty\n2.Clean\n')
    zip_or_not = input('\nDo you want TWRP flashable zip? (y/N):\n')

    # Build kernel as required
    if build_type != '1':
        if path.isdir(f'{kernel_dir}/output'):
            cleanup(pre=True)
        else:
            print('Unable to find existing output directory, skipping pre-cleanup!')
    make_kernel()

    if zip_or_not == 'y' or 'yes':
        make_zip()
        cleanup(post=True)


if __name__ == '__main__':
    build()
