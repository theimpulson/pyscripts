#
# Copyright (C) 2020 The LineageOS Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import subprocess

from datetime import datetime
from hashlib import sha1
from pathlib import Path
from textwrap import dedent, indent
from time import sleep
from shutil import copy


class ExtractUtils:
    """
    ExtractUtils contains functions which are helpful in generating a build system compatible
    vendor directory.
    """
    def __init__(self):
        self.device = None
        self.vendor = None
        self.lineage_root = None
        self.output_path = None
        self.setup_files = None

    def setup_vendor(self, device='', vendor='', lineage_root=''):
        """
        Takes argument from user and sets variables to be used across various functions
        Input: (device name, vendor name, lineage's source root path)
        """
        self.device = device
        self.vendor = vendor
        self.lineage_root = lineage_root
        self.output_path = f'{lineage_root}/vendor/{vendor}/{device}'
        self.setup_files = [
            f'{self.output_path}/{device}-vendor.mk',
            f'{self.output_path}/Android.bp',
            f'{self.output_path}/Android.mk',
            f'{self.output_path}/BoardConfigVendor.mk'
        ]

        # Create initial vendor dir & files
        Path(self.output_path).mkdir(parents=True, exist_ok=True)
        for args in self.setup_files:
            open(args, 'a').close()

    def adb_connected(self):
        """
        Returns True if adb is up and not in recovery
        """
        process = subprocess.Popen(['adb', 'get-state'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if process.returncode == 0 and 'device' in str(output):
            return True
        else:
            return False

    def get_hash(self, file):
        """
        Returns sha1 of the given file
        """
        with open(file, 'rb') as target:
            return sha1(target.read()).hexdigest()

    @staticmethod
    def fix_xml(xml):
        """
        Fixes the given xml file by moving the version declaration to the header if not already at it
        """
        with open(xml, 'r+') as file:
            matter = file.readlines()
            header = matter.index("\n".join(s for s in matter if '<?xml version' in s))
            if header != 0:
                matter.insert(0, matter.pop(header))
                file.seek(0)
                file.writelines(matter)
                file.truncate()

    def init_adb_connection(self):
        """
        Depends upon: adb_connected function
        Starts adb server and waits for the device
        """
        subprocess.run(['adb', 'start-server'])
        while self.adb_connected() is False:
            print('No device is online. Waiting for one...')
            print('Please connect USB and/or enable USB debugging')
            subprocess.run(['adb', 'wait-for-device'])
        else:
            print('\nDevice Found')

        # Check if device is using a TCP connection
        using_tcp = False
        output = subprocess.check_output(['adb', 'devices']).decode('ascii').splitlines()
        device_id = output[1]
        if ":" in device_id:
            using_tcp = True
            device_id = device_id.split(":", 1)[0] + ':5555'

        # Start adb as root if build type is not "user"
        build_type = subprocess.check_output(['adb', 'shell', 'getprop', 'ro.build.type']).decode('ascii').replace('\n', '')
        if build_type == 'user':
            pass
        else:
            subprocess.run(['adb', 'root'])
            sleep(1)
            # Connect again as starting adb as root kills connection
            if using_tcp:
                subprocess.run(['adb', 'connect', device_id])
            else:
                subprocess.run(['adb', 'wait-for-device'])

    def target_file(self, spec):
        """
        Input: spec in the form of 'src[:dst][;args]'
        Output: 'dst' if present, 'src' otherwise
        """
        if ':' in spec:
            dst = spec.split(':', 1)[1]
        else:
            dst = spec
        # Check if dst contains sha1sum delimited by '|'
        if '|' in dst:
            return dst.split('|', 1)[0]
        else:
            return dst

    def target_list(self, prop_list, content=''):
        """
        Takes a list and content type as argument and returns a filtered list which contains desired contents
        """
        work_list = []
        for item in list(prop_list):
            if content is 'packages':
                if str(item).startswith('-'):
                    work_list.append(item)
            elif content is 'copy':
                if not str(item).startswith(('-', '#')):
                    work_list.append(item)
            else:
                if not str(item).startswith('#'):
                    if str(item).startswith('-'):
                        work_list.append(str(item).split('-', 1)[1])
                    else:
                        work_list.append(item)

        # Cleanup the list
        work_list = [i.replace('\n', '') for i in work_list]  # new lines
        work_list = list(filter(None, work_list))  # empty strings
        for n, i in enumerate(work_list):
            work_list[n] = self.target_file(i)  # sha|args
        work_list = list(dict.fromkeys(work_list))  # duplicates

        # Sort and return it
        work_list.sort()
        return work_list

    def write_headers(self, args):
        """
        Cleans and writes LineageOS's copyright header to the given file.
        variables: 'device', 'vendor' must be set before using this function.
        Accepted file extensions: '.mk', '.bp'
        setup_vendor function must be run before using this function
        """
        if Path(args).suffix == '.mk':
            comment = '# '
        else:
            comment = '// '

        current_year = datetime.now().year
        file_license = dedent(f'''\

        Copyright (C) 2019-{current_year} The LineageOS Project

        Licensed under the Apache License, Version 2.0 (the "License");
        you may not use this file except in compliance with the License.
        You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

        Unless required by applicable law or agreed to in writing, software
        distributed under the License is distributed on an "AS IS" BASIS,
        WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
        See the License for the specific language governing permissions and
        limitations under the License.

        This file is generated by device/{self.vendor}/{self.device}/setup-makefiles.sh

        ''')

        header = indent(file_license, comment, lambda line: True)
        with open(args, 'w') as target:
            target.write(header + '\n')

    def write_product_copy_files(self, prop_list):
        """
        Takes a list as argument and writes files to copied into device-vendor.mk file
        setup_vendor function must be run before using this function
        """
        # Filter the given list to remove package targets
        work_list = self.target_list(prop_list, "copy")

        # Append proper partition suffixes to copy the target into
        app_list = []
        for item in work_list:
            if str(item).startswith('vendor'):
                suffix = '$(TARGET_COPY_OUT_VENDOR)/'
            elif str(item).startswith('product'):
                suffix = '$(TARGET_COPY_OUT_PRODUCT)/'
            elif str(item).startswith('odm'):
                suffix = '$(TARGET_COPY_OUT_ODM)/'
            else:
                suffix = '$(TARGET_COPY_OUT_SYSTEM)/'
            app_list.append(f'{suffix}{item}' + ' \\')

        # Remove backslash from the last line
        app_list[-1] = app_list[-1].replace(' \\', '')

        # Create a dict based on the prop_list and app_list
        fin_files = dict(zip(work_list, app_list))

        with open(self.setup_files[0], 'a') as target:
            target.write('PRODUCT_SOONG_NAMESPACES += \\' + '\n')
            target.write('    ' + f'vendor/{self.vendor}/{self.device}' + '\n')
            target.write('\n' + 'PRODUCT_COPY_FILES += \\' + '\n')

        for key, values in fin_files.items():
            with open(self.setup_files[0], 'a') as target:
                target.write('    ' + f'vendor/{self.vendor}/{self.device}/proprietary/' + key + ':' + values + "\n")

        # Create dummy directories to copy files into
        for files in work_list:
            dir_path = f'{self.output_path}/proprietary/' + str(Path(files).parent)
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def write_product_packages(self, prop_list):
        """Writes product packages into blueprint files from the given list"""
        # Filter the given list to remove copy targets
        work_list = self.target_list(prop_list, "packages")

        with open(self.setup_files[1], 'a') as path:
            path.write('soong_namespace {\n')
            path.write('}\n')

        # Set variables and module format to write for the given product
        for item in work_list:
            org_target = str(item)
            target = org_target.split('-', 1)[1]
            name = Path(item).stem
            suffix = Path(item).suffix
            src = f'proprietary/{target}'

            if target.startswith('vendor/'):
                specific = 'soc_specific: true,'
            elif target.startswith('product/'):
                specific = 'product_specific: true,'
            elif target.startswith('odm/'):
                specific = 'device_specific: true,'
            else:
                specific = None

            if '.apk' == suffix:
                module_format = dedent(f'''\
                android_app_import {{
                        name: "{name}",
                        owner: "{self.vendor}",
                        apk: "{src}",
                        certificate: "platform",
                        {'privileged: true,' if 'priv-app' in src else ''}
                        dex_preopt: {{
                                enabled: false,
                        }},
                        {specific if specific is not None else ''}
                }}''').replace('\n\n', '\n')
            elif '.jar' == suffix:
                module_format = dedent(f'''\
                dex_import {{
                        name: "{name}",
                        owner: "{self.vendor}",
                        jars: ["{src}"],
                        {specific if specific is not None else ''}
                }}''').replace('\n\n', '\n')
            elif '.so' == suffix:
                # Check if both 32 & 64 bit targets exist
                libpath = org_target.split('/' + name, 1)[0]
                src32 = libpath + f'/{name}.so'
                src64 = libpath + f'64/{name}.so'
                if src32 and src64 in work_list:
                    work_list.remove(src64)  # Remove 64 bit target to avoid duplication
                    multi = 'both'
                    src32 = src32.split('-', 1)[1]
                    src64 = src64.split('-', 1)[1]
                    module_format = dedent(f'''\
                        cc_prebuilt_library_shared {{
                                name: "{name}",
                                owner: "{self.vendor}",
                                strip: {{
                                        none: true,
                                }},
                                target: {{
                                        android_arm: {{
                                                srcs: ["proprietary/{src32}"],
                                        }},
                                        android_arm64: {{
                                                srcs: ["proprietary/{src64}"],
                                        }},
                                }},
                                compile_multilib: "{multi}",
                                prefer: true,
                                {specific if specific is not None else ''}
                        }}''').replace('\n\n', '\n')
                else:
                    if 'lib/' in target:
                        multi = '32'
                    else:
                        multi = '64'
                    module_format = dedent(f'''\
                        cc_prebuilt_library_shared {{
                                name: "{name}",
                                owner: "{self.vendor}",
                                strip: {{
                                        none: true,
                                }},
                                target: {{
                                        android_arm{'64' if multi == '64' else ''}: {{
                                                srcs: ["{src}"],
                                        }},
                                }},
                                compile_multilib: "{multi}",
                                prefer: true,
                                {specific if specific is not None else ''}
                        }}''').replace('\n\n', '\n')
            else:
                module_format = f'Missing format for "{org_target}"'

            dir_path = f'{self.output_path}/' + str(Path(src).parent)
            with open(self.setup_files[1], 'a') as path:
                path.write('\n')
                path.write(module_format + '\n')
                # Create dummy directories to copy the file into as well
                Path(dir_path).mkdir(parents=True, exist_ok=True)

    def write_guards(self):
        """
        Writes build guards for the device into Android.mk file
        setup_vendor function must be run before using this function
        """
        guard = dedent(f'''\
        LOCAL_PATH := $(call my-dir)
        ifneq ($(filter {self.device},$(TARGET_DEVICE)),)
        endif
        ''')
        with open(self.setup_files[2], 'a') as target:
            target.write(guard)

    def extract_files(self, prop_file, path=''):
        """
        Generates a vendor dir from the given list (path to list must be absolute)
        setup_vendor function must be run before using this function
        """
        # Write required contents into the file
        for files in self.setup_files:
            self.write_headers(files)
        self.write_guards()
        with open(prop_file) as file:
            matter = file.readlines()
        self.write_product_copy_files(matter)
        self.write_product_packages(matter)

        # pull_list = []
        # prop_list = self.target_list(matter)
        #
        # for files in prop_list:
        #     # Check for pinned files that they exists and matches the given sha1
        #     if '|' in files:
        #         hash_target = f'{self.output_path}/proprietary/' + self.target_file(files)
        #         if Path(hash_target).exists():
        #             if str(files).split('|', 1)[1] == self.get_hash(hash_target):
        #                 pass
        #             else:
        #                 pull_list.append(files)
        #         else:
        #             pull_list.append(files)
        #     else:
        #         pull_list.append(files)
        #
        # # Copy the files
        # for files in prop_list:
        #     copy(f'{path}/{files}', f'{self.output_path}/proprietary/{files}')
