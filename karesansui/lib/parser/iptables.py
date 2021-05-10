#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Karesansui Core.
#
# Copyright (C) 2009-2012 HDE, Inc.
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

import os
import re
import sys
import time

from karesansui.lib.dict_op import DictOp
from karesansui.lib.parser.base.line_parser import lineParser as Parser
from karesansui.lib.utils import array_replace
from karesansui.lib.utils import preprint_r


"""
Define Variables for This Parser
"""
PARSER_COMMAND_IPTABLES="/sbin/iptables"
PARSER_COMMAND_IPTABLES_SAVE="/sbin/iptables-save"
PARSER_COMMAND_IPTABLES_RESTORE="/sbin/iptables-restore"
PARSER_IPTABLES_CONF="/etc/sysconfig/iptables"
PARSER_IPTABLES_INITRD="/etc/init.d/iptables"
PARSER_IPTABLES_INITRD_ACTIONS="start|stop|restart|condrestart|status|panic|save"

PARSER_IPTABLES_CONF_HEADER="(# Generated by .* on ).*"
PARSER_IPTABLES_CONF_FOOTER="(# Completed on ).*"


class iptablesParser:

    _module = "iptables"

    def __init__(self):
        self.dop = DictOp()
        self.dop.addconf(self._module,{})

        self.parser = Parser()
        self.base_parser_name = self.parser.__class__.__name__
        pass

    def source_file(self):
        retval = [PARSER_IPTABLES_CONF]

        return retval

    def read_conf(self,extra_args=None):
        retval = {}

        self.parser.set_source_file([PARSER_IPTABLES_CONF])
        self.dop.addconf(self._module,{})

        conf_arr = self.parser.read_conf()
        try:
            lines = conf_arr[PARSER_IPTABLES_CONF]['value']
            lint = self.do_lint("\n".join(lines))
            self.dop.set(self._module,["config"],lines)
            self.dop.set(self._module,["lint"]  ,lint)
        except:
            pass

        cmdfile = "cmd:%s" % PARSER_COMMAND_IPTABLES_SAVE
        self.parser.set_source_file([cmdfile])
        conf_arr = self.parser.read_conf()
        try:
            lines = conf_arr[cmdfile]['value']
            self.dop.set(self._module,["status"],lines)
        except:
            pass

        self.parser.set_source_file([PARSER_IPTABLES_CONF])

        self.dop.set(self._module,['@BASE_PARSER'],self.base_parser_name)
        #self.dop.preprint_r(self._module)
        return self.dop.getconf(self._module)

    def write_conf(self,conf_arr={},extra_args=None,dryrun=False):
        retval = True

        now = time.strftime("%c",time.localtime())
        try:
            self.dop.addconf("parser",{})

            lines = conf_arr["config"]["value"]
            lines = array_replace(lines,PARSER_IPTABLES_CONF_HEADER,"# Generated by karesansui on %s" % (now,))
            lines = array_replace(lines,PARSER_IPTABLES_CONF_FOOTER,"# Completed on %s" % (now,))
            self.dop.set("parser",[PARSER_IPTABLES_CONF],lines)
            #self.dop.preprint_r("parser")
            arr = self.dop.getconf("parser")
            self.parser.write_conf(arr,dryrun=dryrun)
            self.do_condrestart()
        except:
            pass

        return retval

    def do_start(self):
        return self._do("start")

    def do_stop(self):
        return self._do("stop")

    def do_restart(self):
        return self._do("restart")

    def do_condrestart(self):
        return self._do("condrestart")

    def do_status(self):
        return self._do("status")

    def is_running(self):
        return self.do_status()[0]

    def _do(self,action=None):
        from karesansui.lib.utils import execute_command

        retval = False
        res    = []
        if re.match("^(%s)$" % PARSER_IPTABLES_INITRD_ACTIONS, action):
            command_args = [PARSER_IPTABLES_INITRD,action]
            (ret,res) = execute_command(command_args)
            if ret == 0:
                retval = True
        return [retval,res]

    # reverseがFalseなら設定ファイルをもとに、システムに反映(condrestart)
    # reverseがTrueならシステムの状態をもとに、設定ファイルに反映
    def do_sync(self,reverse=False):
        try:
            self.dop.addconf("parser",self.read_conf())
            if reverse is False:
                self.do_restart()
            else:
                lines = self.dop.get("parser",["status"])
                self.dop.set("parser",["config"],lines)
                conf = self.dop.getconf("parser")
                self.write_conf(conf)
            return True
        except:
            return False

    def do_lint(self,string,lint=True):
        import signal
        import subprocess
        retval = []

        if lint is True:
            (old_ret,old_res) = self.do_status()
            if old_ret is True:
                old_lines = []
                cmdfile = "cmd:%s" % PARSER_COMMAND_IPTABLES_SAVE
                self.parser.set_source_file([cmdfile])
                conf_arr = self.parser.read_conf()
                try:
                    old_lines = conf_arr[cmdfile]['value']
                except:
                    pass
                self.parser.set_source_file([PARSER_IPTABLES_CONF])


        signal.alarm(10)
        if lint is True:
            command_args = [PARSER_COMMAND_IPTABLES_RESTORE,"--test"]
        else:
            command_args = [PARSER_COMMAND_IPTABLES_RESTORE]
        proc = subprocess.Popen(command_args,
                   bufsize=1,
                   shell=True,
                   stdin=subprocess.PIPE,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)

        #proc.stdin.write(string)
        (stdout,stderr) = proc.communicate(string)
        ret = proc.wait()
        signal.alarm(0)

        exclude_strings = [
           "Try `iptables-restore -h' or 'iptables-restore --help' for more information.",
           "iptables-restore v[0-9\.]+: iptables-restore:",
           "iptables-restore v[0-9\.]+: ",
        ]

        new_stderr = []
        for _aline in re.split("[\r\n]+",stderr):
            new_stderr.append(_aline)
        new_stderr = array_replace(new_stderr,exclude_strings,["","",""])
        stderr = "\n".join(new_stderr)
        """
        """

        retval = [ret,stdout,stderr]

        if lint is True:
            if old_ret is True and len(old_lines) != 0:
                self.do_lint("\n".join(old_lines),lint=False)
            elif old_ret is False:
                self.do_stop()

        return retval

"""
"""
if __name__ == '__main__':
    """Testing
    """
    parser = iptablesParser()
    dop = DictOp()
    dop.addconf("dum",parser.read_conf())
    lines = dop.get("dum",['config'])
    lines.append("aa# test")
    lines.append("bb# test")
    lines.append("aa# test")
    #preprint_r(lines)

    dop.set("dum",['config'],lines)
    conf = dop.getconf("dum")
    #preprint_r(conf)

    parser.do_stop()
    print(parser.is_running())
    parser.do_start()
    print(parser.is_running())
    parser.do_stop()
    print(parser.is_running())

    parser.write_conf(conf,dryrun=True)
    #parser.do_sync(True)
    print(parser.do_sync(False))

    contents = open("/etc/sysconfig/iptables.corrupted").read()
    print(parser.do_lint(contents))

