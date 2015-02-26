# -*- coding: utf-8 -*-
#
#  2015-02-25 Cornelius Kölbel <cornelius@privacyidea.org>
#             Initial writup
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
__doc__ = """This contains the HostsMachineResolver which simply resolves
the machines in a file like /etc/hosts.
The machine id is the IP address in this case.

This file is tested in tests/test_lib_machines.py in the class
HostsMachineTestCase
"""

from .base import Machine
from .base import BaseMachineResolver
from .base import MachineResolverError

import netaddr


class HostsMachineResolver(BaseMachineResolver):

    type = "hosts"

    def get_machines(self, machine_id=None, hostname=None, ip=None):
        machines = []

        f = open(self.filename, "r")
        try:
            for line in f:
                split_line = line.split()
                line_id = split_line[0]
                line_ip = netaddr.IPAddress(split_line[0])
                line_hostname = split_line[1:]
                if machine_id:
                    if machine_id == line_id:
                        return [Machine(line_id,
                                        hostname=line_hostname, ip=line_ip)]
                elif hostname or ip:
                    h_match = not hostname or (hostname in line_hostname)
                    i_match = not ip or (ip == line_ip)
                    if h_match and i_match:
                        machines.append(Machine(line_id,
                                                 hostname=line_hostname,
                                                 ip=line_ip))
                else:
                    machines.append(Machine(line_id, hostname=line_hostname,
                                            ip=line_ip))
        finally:
            f.close()
        return machines

    def get_machine_id(self, hostname=None, ip=None):
        """
        Returns the machine id for a given hostname or IP address.

        If hostname and ip is given, the resolver should also check that the
        hostname matches the IP. If it can check this and hostname and IP do
        not match, then an Exception must be raised.

        :param hostname: The hostname of the machine
        :type hostname: basestring
        :param ip: IP address of the machine
        :type ip: netaddr
        :return: The machine ID, which depends on the resolver
        :rtype: basestring
        """
        machines = self.get_machines()
        for machine in machines:
            h_match = not hostname or machine.has_hostname(hostname)
            i_match = not ip or machine.has_ip(ip)
            if h_match and i_match:
                return machine.id

        return

    def load_config(self, config):
        """
        This loads the configuration dictionary, which contains the necessary
        information for the machine resolver to find and connect to the
        machine store.

        :param config: The configuration dictionary to run the machine resolver
        :type config: dict
        :return: None
        """
        self.filename = config.get("filename")
        if self.filename is None:
            raise MachineResolverError("filename is missing!")

    @classmethod
    def get_config_description(self):
        description = {self.type: {"config": {"filename": "string"}}}
        return description


    @classmethod
    def testconnection(cls, params):
        """
        Test if the given filename exists.

        :param params:
        :return:
        """
        return False, "Not Implemented"