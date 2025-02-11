#!/usr/bin/env python
# -*- coding: utf-8 -*- 
#
# This file is part of Karesansui.
#
# Copyright (C) 2012 HDE, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import time
import re
import os
import sys
from optparse import OptionParser

from ksscommand import KssCommand, KssCommandException, KssCommandOptException

import __cmd__

try:
    import karesansui
    import libvirt
    import libvirtmod
    from karesansui import __app__,__version__,__release__
    from karesansui.lib.virt.virt import KaresansuiVirtConnection
    from karesansui.lib.utils import load_locale
    from karesansui.lib.utils import is_executable, execute_command
    from karesansui.lib.utils import available_virt_uris
    from karesansui.lib.utils import available_virt_mechs

except ImportError as e:
    print("[Error] some packages not found. - %s" % e, file=sys.stderr)
    sys.exit(1)

_ = load_locale()

usage = '%prog [options]'

def getopts():
    optp = OptionParser(usage=usage, version=__version__)
    optp.add_option('-a', '--all',  dest='all', action="store_true", help=_('Print all information'))
    optp.add_option('-i', '--node-info', action="store_true", dest='nodeinfo',help=_('Print node information'))
    optp.add_option('-l', '--list', action="store_true", dest='list',help=_('Print domain list'))
    optp.add_option('-n', '--net-list', action="store_true", dest='netlist',help=_('Print network list'))
    optp.add_option('-p', '--pool-list', action="store_true", dest='poollist',help=_('Print pool list'))
    return optp.parse_args()

COMMAND_VIRSH = "/usr/bin/virsh"
COMMAND_LIGHTTPD = "/usr/sbin/lighttpd"

prog_name = os.path.basename(__file__)

class SysInfo(KssCommand):

    def showKaresansuiVersion(self):
        print(_("Using karesansui: %s %s.%s") %(__app__,__version__,__release__))
        (rc,res) = execute_command([COMMAND_LIGHTTPD,"-v"])
        if rc == 0:
            p = re.compile("lighttpd-([0-9\.]+) .*")
            if p.search(res[0]):
                lighttpdVersion = p.sub("\\1",res[0])
                print(_("Using lighttpd: %s") %(lighttpdVersion))

        try:
            from pysilhouette import __app__      as pysilhouette_app
            from pysilhouette import __version__  as pysilhouette_ver
            from pysilhouette import __release__  as pysilhouette_rel
            print(_("Using pysilhouette: %s %s.%s") %(pysilhouette_app,pysilhouette_ver,pysilhouette_rel))
        except:
            pass

    def process(self):
        (opts, args) = getopts()

        start_msg = _("Generated by %s on %s") % (prog_name,time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
        print("# " + start_msg)

        if is_executable(COMMAND_VIRSH):
            old_lang = os.environ.get('LANG')
            os.environ['LANG'] = "C"

            if opts.all is True or (opts.list is not True and opts.netlist is not True and opts.nodeinfo is not True and opts.poollist is not True):
                """ Show version """
                print("")
                print("## Version")
                (rc,res) = execute_command([COMMAND_VIRSH,"version"])
                if rc == 0:
                    for line in res:
                        if line != "":
                            print(line)
                self.showKaresansuiVersion()

            if opts.all is True:
                """ Show uri """
                print("")
                print("## URI")
                (rc,res) = execute_command([COMMAND_VIRSH,"uri"])
                if rc == 0:
                    print(_("Connecting URI: %s") %(res[0]))

                """ Show hostname """
                print("")
                print("## Hostname")
                (rc,res) = execute_command([COMMAND_VIRSH,"hostname"])
                if rc == 0:
                    print(_("Hypervisor hostname: %s") %(res[0]))

            if opts.all is True or opts.nodeinfo is True:
                """ Show nodeinfo """
                print("")
                print("## Node Information")
                (rc,res) = execute_command([COMMAND_VIRSH,"nodeinfo"])
                if rc == 0:
                    for line in res:
                        if line != "":
                            print(line)

            if opts.all is True or opts.list is True:
                """ Show dom list """
                print("")
                print("## Domain List")
                (rc,res) = execute_command([COMMAND_VIRSH,"list","--all"])
                if rc == 0:
                    for line in res:
                        if line != "":
                            print(line)

            if opts.all is True or opts.netlist is True:
                """ Show net list """
                print("")
                print("## Network List")
                (rc,res) = execute_command([COMMAND_VIRSH,"net-list","--all"])
                if rc == 0:
                    for line in res:
                        if line != "":
                            print(line)

            if opts.all is True or opts.poollist is True:
                """ Show pool list """
                print("")
                print("## Pool List")
                (rc,res) = execute_command([COMMAND_VIRSH,"pool-list","--all"])
                if rc == 0:
                    for line in res:
                        if line != "":
                            print(line)

            os.environ['LANG'] = old_lang
        else:
            try:
                conn = libvirt.openReadOnly(None)
                hypervisor = conn.getType()

                if opts.all is True or (opts.list is not True and opts.netlist is not True and opts.nodeinfo is not True and opts.poollist is not True):
                    """ Show version """
                    print("")
                    print("## Version")
                    ret = libvirtmod.virGetVersion(hypervisor)
                    libVersion = ret[0]
                    apiVersion = ret[1]

                    libVersion_major = libVersion / 1000000
                    libVersion %= 1000000
                    libVersion_minor = libVersion / 1000
                    libVersion_rel = libVersion % 1000
                    apiVersion_major = apiVersion / 1000000
                    apiVersion %= 1000000
                    apiVersion_minor = apiVersion / 1000
                    apiVersion_rel = apiVersion % 1000

                    print(_("Using library: libvir %d.%d.%d") %(libVersion_major, libVersion_minor, libVersion_rel))
                    print(_("Using API: %s %d.%d.%d") %(hypervisor, apiVersion_major, apiVersion_minor, apiVersion_rel))

                    try:
                        # See https://www.redhat.com/archives/libvir-list/2010-January/msg00723.html
                        ret = libvirtmod.virConnectGetVersion(conn._o)
                        hvVersion = ret
                        hvVersion_major = hvVersion / 1000000
                        hvVersion %= 1000000
                        hvVersion_minor = hvVersion / 1000
                        hvVersion_rel = hvVersion % 1000
                        print(_("Running hypervisor: %s %d.%d.%d") %(hypervisor, hvVersion_major, hvVersion_minor, hvVersion_rel))
                    except:
                        if hypervisor == "QEMU":
                            (rc,res) = execute_command(["qemu","--version"])
                            if rc == 0:
                                p = re.compile("QEMU PC emulator version ([0-9\.]+),.*")
                                if p.search(res[0]):
                                    qemuVersion = p.sub("\\1",res[0])
                                    print(_("Running hypervisor: %s %s") %(hypervisor, qemuVersion))

                    self.showKaresansuiVersion()

                if opts.all is True:
                    """ Show uri """
                    print("")
                    print("## URI")
                    uri = conn.getURI()
                    print(_("Connecting URI: %s") %(uri))

                    """ Show hostname """
                    print("")
                    print("## Hostname")
                    hostname = conn.getHostname()
                    print(_("Hypervisor hostname: %s") %(hostname))

                if opts.all is True or opts.nodeinfo is True:
                    """ Show nodeinfo """
                    print("")
                    print("## Node Information")
                    nodeInfo = conn.getInfo()
                    print("%-20s %s"    % (_("CPU model:")         ,nodeInfo[0]))
                    print("%-20s %s"    % (_("CPU(s):")            ,nodeInfo[2]))
                    print("%-20s %s MHz"% (_("CPU frequency:")     ,nodeInfo[3]))
                    print("%-20s %s"    % (_("CPU socket(s):")     ,nodeInfo[5]))
                    print("%-20s %s"    % (_("Core(s) per socket:"),nodeInfo[6]))
                    print("%-20s %s"    % (_("Thread(s) per core:"),nodeInfo[7]))
                    print("%-20s %s"    % (_("NUMA cell(s):")      ,nodeInfo[4]))
                    print("%-20s %lu kB"% (_("Memory Size:")  ,(float)(nodeInfo[1])*1024))

                if opts.all is True or opts.list is True:
                    """ Show dom list """
                    print("")
                    print("## Domain List")
                    state_flags = [
                                  "no state",    # VIR_DOMAIN_NOSTATE
                                  "running",     # VIR_DOMAIN_RUNNING
                                  "idle",        # VIR_DOMAIN_BLOCKED
                                  "paused",      # VIR_DOMAIN_PAUSED
                                  "in shutdown", # VIR_DOMAIN_SHUTDOWN
                                  "shut off",    # VIR_DOMAIN_SHUTOFF
                                  "crashed",     # VIR_DOMAIN_CRASHED
                                  ]
                    #print "%3s %-20s %s" %(_("Id"), _("Name"), _("State"))
                    #print "----------------------------------"
                    print("%3s %-20s %-12s %-37s %-10s %-12s %-12s %-3s %-12s" %(_("Id"), _("Name"), _("State"), _("UUID"), _("Autostart"), _("MaxMem"), _("Memory"), _("Vcpus"), _("CPUTime"), ))
                    print("---------------------------------------------------------------------------")

                    domains_ids = conn.listDomainsID()
                    for id in domains_ids:
                        dom = conn.lookupByID(id)
                        name    = dom.name()
                        domID   = id
                        domInfo = dom.info()
                        domUUID = dom.UUIDString()
                        domAutostart = dom.autostart()
                        if domAutostart == True:
                            locale_domAutostart = _("enable")
                        else:
                            locale_domAutostart = _("disable")
                        state = domInfo[0]
                        if domID == -1:
                            #print "%3s %-20s %s" %("-", name, state_flags[state])
                            print("%3s %-20s %-12s %-37s %-10s %-12ld %-12ld %-3d %-12ld" %("-", name, state_flags[state], domUUID, locale_domAutostart, domInfo[1], domInfo[2], domInfo[3], domInfo[4]))
                        else:
                            #print "%3d %-20s %s" %(domID, name, state_flags[state])
                            print("%3d %-20s %-12s %-37s %-10s %-12ld %-12ld %-3d %-12ld" %(domID, name, state_flags[state], domUUID, locale_domAutostart, domInfo[1], domInfo[2], domInfo[3], domInfo[4]))

                    defined_domains = conn.listDefinedDomains()
                    for name in defined_domains:
                        dom = conn.lookupByName(name)
                        #print dom.memoryStats()
                        domID   = dom.ID()
                        domInfo = dom.info()
                        domUUID = dom.UUIDString()
                        domAutostart = dom.autostart()
                        if domAutostart == True:
                            locale_domAutostart = _("enable")
                        else:
                            locale_domAutostart = _("disable")
                        state = domInfo[0]
                        if domID == -1:
                            #print "%3s %-20s %s" %("-", name, state_flags[state])
                            print("%3s %-20s %-12s %-37s %-10s %-12ld %-12ld %-3d %-12ld" %("-", name, state_flags[state], domUUID, locale_domAutostart, domInfo[1], domInfo[2], domInfo[3], domInfo[4]))
                        else:
                            #print "%3d %-20s %s" %(domID, name, state_flags[state])
                            print("%3d %-20s %-12s %-37s %-10s %-12ld %-12ld %-3d %-12ld" %(domID, name, state_flags[state], domUUID, locale_domAutostart, domInfo[1], domInfo[2], domInfo[3], domInfo[4]))

                if opts.all is True or opts.netlist is True:
                    """ Show net list """
                    print("")
                    print("## Network List")
                    #print "%-20s %-10s %-10s" %(_("Name"), _("State"), _("Autostart"))
                    #print "-----------------------------------------"
                    print("%-20s %-10s %-37s %-10s" %(_("Name"), _("State"), _("UUID"), _("Autostart"), ))
                    print("--------------------------------------------------------------------------")
                    networks = conn.listNetworks()
                    for name in networks:
                        net = conn.networkLookupByName(name)
                        uuid = net.UUIDString()
                        autostart = net.autostart()
                        if autostart == True:
                            locale_autostart = _("yes")
                        else:
                            locale_autostart = _("no")

                        print("%-20s %-10s %-37s %-10s" %(name, _("Active"), uuid, locale_autostart))

                    defined_networks = conn.listDefinedNetworks()
                    for name in defined_networks:
                        net = conn.networkLookupByName(name)
                        uuid = net.UUIDString()
                        autostart = net.autostart()
                        if autostart == True:
                            locale_autostart = _("yes")
                        else:
                            locale_autostart = _("no")

                        print("%-20s %-10s %-37s %-10s" %(name, _("Inactive"), uuid, locale_autostart))

                if opts.all is True or opts.poollist is True:
                    """ Show pool list """
                    #taizoa
                    print("")
                    print("## Pool List")
                    print("%-20s %-10s %-37s %-10s" %(_("Name"), _("State"), _("UUID"), _("Autostart"), ))
                    print("--------------------------------------------------------------------------")
                    pools = conn.listStoragePools()
                    for name in pools:
                        pool = conn.storagePoolLookupByName(name)
                        uuid = pool.UUIDString()
                        autostart = pool.autostart()
                        if autostart == True:
                            locale_autostart = _("yes")
                        else:
                            locale_autostart = _("no")

                        print("%-20s %-10s %-37s %-10s" %(name, _("Active"), uuid, locale_autostart))

                    defined_pools = conn.listDefinedStoragePools()
                    for name in defined_pools:
                        pool = conn.storagePoolLookupByName(name)
                        uuid = pool.UUIDString()
                        autostart = pool.autostart()
                        if autostart == True:
                            locale_autostart = _("yes")
                        else:
                            locale_autostart = _("no")

                        print("%-20s %-10s %-37s %-10s" %(name, _("Inactive"), uuid, locale_autostart))

            except:
                pass

        if opts.all is True:
            """ Show available uris """
            print("")
            print("## Available URIs")
            for mech,uri in available_virt_uris().items():
               print(uri)

            """ Show available mechs """
            print("")
            print("## Available mechanisms")
            for mech in available_virt_mechs():
               print(mech)

            """ Show installed packages """
            print("")
            print("## Installed packages")
            (rc,res) = execute_command(["rpm","-qa",'--queryformat=%{NAME}\t%{VERSION}\t%{RELEASE}\t%{INSTALLTIME}\t%{BUILDHOST}\n'])
            if rc == 0:
                print("%-25s %-10s %-10s %-20s" %(_("Name"), _("Version"), _("Release"), _("InstallTime"), ))
                print("------------------------------------------------------------------")
                p = re.compile("hde\.co\.jp")
                output = []
                for aline in res:
                    arr = aline.split("\t")
                    if p.search(arr[4]):
                        str = "%-25s %-10s %-10s %-20s" %(arr[0],arr[1],arr[2],time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(float(arr[3]))),)
                        output.append(str)
                print("\n".join(sorted(output)))

        finish_msg = _("Completed on %s") % time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
        print("")
        print("# " + finish_msg)

        return True

if __name__ == "__main__":
    target = SysInfo()
    sys.exit(target.run())
