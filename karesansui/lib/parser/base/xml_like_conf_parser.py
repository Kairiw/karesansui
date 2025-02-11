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

from karesansui.lib.file.configfile import ConfigFile
from karesansui.lib.dict_op import DictOp
from karesansui.lib.utils import preprint_r, str_repeat

"""
XMLライクな設定ファイルのパーサ
コメントを扱える
書き込み順を扱える
複数設定可能なオプションを扱える LoadPluginとか

有効な設定行の間のコメントは、次の有効な設定のコメントとみなす

---------------------------------
# comment-1
# comment-2

foo bar1 # comment-3
---------------------------------
上記のようなファイルの場合、配列は以下のようになります

value["foo"]["value"] =
  [
    "bar1",
    ["# comment-1","#comment-2"],
    "# comment-3",
  ]
"""
class xmlLikeConfParser:

    _delim               = "[ \t]+"
    _new_delim           = " "
    _comment             = "#"
    _reserved_key_prefix = "@"
    _indent              = "  "

    _module  = "xml_like_conf_parser"
    _footer  = "-- Generated by karesansui"

    def __init__(self,paths=[]):
        self.dop = DictOp()
        self.dop.addconf(self._module,{})
        self.set_source_file(paths)

        self.opt_uni   = ['PIDFile']
        self.opt_multi = ['LoadPlugin','Include']
        self.opt_sect  = ['Directory','VirtualHost','View']

    def set_opt_uni(self, opts):
        self.opt_uni = opts

    def set_opt_multi(self, opts):
        self.opt_multi = opts

    def set_opt_sect(self, opts):
        self.opt_sect = opts

    def set_delim(self, delim=" "):
        self._delim = delim

    def set_new_delim(self, delim=" "):
        self._new_delim = delim

    def set_comment(self, comment="#"):
        self._comment = comment

    def set_reserved_key_prefix(self, prefix="@"):
        self._reserved_key_prefix = prefix

    def set_footer(self, footer=""):
        self._footer = footer

    def set_source_file(self,paths=[]):
        if type(paths) == str:
            paths = [paths]
        self.paths = paths
        return True

    def get_source_file(self):
        return self.paths

    def source_file(self):
        return self.get_source_file()

    def build_value(self, value=None, precomment=[], postcomment=None):
        if type(precomment) == str:
            precomment = [precomment]
        return [value, [precomment, postcomment], ]

    def read_conf(self):
        retval = {}
        orders_key = "%sORDERS" % (self._reserved_key_prefix,)

        for _afile in self.source_file():
            res = ConfigFile(_afile).read()
            self.orders = []
            self.dop.set(self._module,[_afile],self._read_conf(res))
            self.dop.set(self._module,[_afile,orders_key],self.orders)

        return self.dop.getconf(self._module)

    def _read_conf(self,lines,level=0):

        dop = DictOp()
        dop.addconf("__",{})

        pre_comment  = []   # 設定の前のコメント リスト配列
        post_comment = None # 設定行のコメント 文字列
        _in_section = False
        _res = []
        for _aline in lines:

            if _in_section is True:
                regex = "[ \t]*(?P<comment>#*)[ \t]*</(?P<key>%s)>" % _section_key #'|'.join(self.opt_sect)
                _regex = re.compile(r"%s" % regex)
                m = _regex.match(_aline)
                if m:
                    _comment = m.group('comment')
                    _key     = m.group('key').strip()
                    values = self.build_value(self._read_conf(_res,level),pre_comment,post_comment)
                    dop.set("__",[_key,_section_val],values)
                    if _comment != "":
                        dop.comment("__",[_key,_section_val])
                    if level == 1:
                        self.orders.append([_key,_section_val])
                    pre_comment  = []
                    post_comment = None
                    _in_section = False
                    _res = []
                    level = level - 1
                else:
                    _res.append(_aline)

            else:

                _aline = _aline.rstrip('\r\n')

                if _aline.strip() == "":
                    pre_comment.append(_aline)
                    continue

                match = False
                for _type in ['uni','multi','sect']:
                    exec("regex = '|'.join(self.opt_%s)" % _type)
                    if _type == "sect":
                        regex = "[ \t]*(?P<comment>#*)[ \t]*<(?P<key>%s)(?P<section>.*)>" % regex
                    elif _type == "multi":
                        regex = "[ \t]*(?P<comment>#*)[ \t]*(?P<key>%s)[ \t]+(?P<value>.+)"  % regex
                    elif _type == "uni":
                        regex = "[ \t]*(?P<comment>#*)[ \t]*(?P<key>%s)[ \t]+(?P<value>.+)"  % regex

                    _regex = re.compile(r"%s" % regex)
                    m = _regex.match(_aline)
                    if m:
                        match = True
                        _comment = m.group('comment')
                        _key     = m.group('key').strip()
                        if _type == "sect":
                            _section_key = _key
                            _section_val = re.sub(r"[\"']","",m.group('section').strip())
                            _in_section = True
                            level = level + 1
                        elif _type == "multi":
                            _value = m.group('value').strip()
                            if _value.find(self._comment) > 0:
                                post_comment = _value[_value.find(self._comment):]
                            _value = re.sub("%s$" % post_comment, "", _value).rstrip()
                            values = self.build_value(_value,pre_comment,post_comment)
                            dop.set("__",[_key,_value],values)
                            if _comment != "":
                                dop.comment("__",[_key,_value])
                            if level == 0:
                                self.orders.append([_key,_value])
                            pre_comment  = []
                            post_comment = None
                        elif _type == "uni":
                            _value   = m.group('value').strip()
                            if _value.find(self._comment) > 0:
                                post_comment = _value[_value.find(self._comment):]
                            _value = re.sub("%s$" % post_comment, "", _value).rstrip()
                            values = self.build_value(_value,pre_comment,post_comment)
                            dop.set("__",[_key],values)
                            if _comment != "":
                                dop.comment("__",[_key])
                            if level == 0:
                                self.orders.append([_key])
                            pre_comment  = []
                            post_comment = None
                        break

                if match is False:

                    # ブラケットディレクティブのパラメータは除外する (よって、ブラケットディレクティブは全ての定義が必要！)
                    # example: "<undefined_directive 'foobar'>"
                    regex_exclude1 = "[ \t]*(?P<comment>#*)[ \t]*(?P<key>%s)[ \t]" % '|'.join(self.opt_sect)
                    _regex_exclude1 = re.compile(r"%s" % regex_exclude1)

                    # 未定義のパラメータの値がクオートせずにスペース区切りで3つ以上の値を指定している場合はコメント行とみなす
                    # example: "# Read this configuration file"
                    regex_exclude2 = "[ \t]*#+[ \t]*[^ \t]+([ \t]+[^ \t]+){3,}"
                    _regex_exclude2 = re.compile(r"%s" % regex_exclude2)

                    # 未定義のパラメータの値がクオートせずにスペース区切りで2つ以上の値を指定していて、かつ、最後が:で終わる場合はコメント行とみなす
                    # example: "# Read this configuration:"
                    regex_exclude3 = "[ \t]*#+[ \t]*[^ \t]+([ \t]+[^ \t]+){2,}:$"
                    _regex_exclude3 = re.compile(r"%s" % regex_exclude3)

                    # 未定義のパラメータの値が0個以上で、かつ、最後が:で終わる場合はコメント行とみなす
                    # example: "# Read #"
                    regex_exclude4 = "[ \t]*#+[ \t]*[^ \t]+.+[ \t]+#+$"
                    _regex_exclude4 = re.compile(r"%s" % regex_exclude4)

                    m1 = _regex_exclude1.match(_aline)
                    m2 = _regex_exclude2.match(_aline)
                    m3 = _regex_exclude3.match(_aline)
                    m4 = _regex_exclude4.match(_aline)
                    if not m1 and not m2 and not m3 and not m4:

                        # opt_xxxに未定義のパラメータはuniパラメータとする
                        regex = "[ \t]*(?P<comment>#*)[ \t]*(?P<key>[A-Z][^ \t]+)[ \t]+(?P<value>.+)"
                        _regex = re.compile(r"%s" % regex)
                        m = _regex.match(_aline)
                        if m:
                            _comment = m.group('comment')
                            _key     = m.group('key').strip()
                            _value   = m.group('value').strip()
                            if _value.find(self._comment) > 0:
                                post_comment = _value[_value.find(self._comment):]
                            _value = re.sub("%s$" % post_comment, "", _value).rstrip()
                            values = self.build_value(_value,pre_comment,post_comment)
                            dop.set("__",[_key],values)
                            if _comment != "":
                                dop.comment("__",[_key])
                            if level == 0:
                                self.orders.append([_key])
                            pre_comment  = []
                            post_comment = None
                            match = True

                if match is False:

                    if _aline.lstrip()[0:1] == self._comment:
                        footer_regex = re.compile(self._footer)
                        m = footer_regex.search(_aline)
                        if not m: 
                            comment = _aline[_aline.find(self._comment):]
                            pre_comment.append(comment)
                            continue

        if len(pre_comment) > 0:
            eof_key   = "%sEOF"    % (self._reserved_key_prefix,)
            new_value = self.build_value("",pre_comment,post_comment)
            dop.set("__",[eof_key],new_value)

        return dop.getconf("__")


    def _value_to_lines(self,conf_arr,level=0):
        lines = []
        orders_key = "%sORDERS" % (self._reserved_key_prefix,)

        dop = DictOp()
        dop.addconf("__",conf_arr)

        for _k,_v in dop.getconf("__").items():

            action = dop.action("__",[_k])
            if action == "delete":
                continue

            iscomment = dop.iscomment("__",[_k])

            value = dop.get("__",[_k])

            if type(value) == list:

                _val          = value[0]

                if type(_val) != dict:
                    _pre_comment  = value[1][0]
                    _post_comment = value[1][1]

                    pre_comment = []
                    try:
                        for _aline in _pre_comment:
                            if _aline.strip() == "":
                                pass
                            elif _aline[0:1] != self._comment:
                                _prefix = ""
                                if level > 0:
                                    _prefix += str_repeat(self._indent,level)
                                _prefix += self._comment
                                _aline = "%s %s" % (_prefix,_aline,)
                            pre_comment.append(_aline)
                    except:
                        pass

                    if len(pre_comment) > 0:
                        #preprint_r(pre_comment)
                        lines = lines + pre_comment

                    post_comment = _post_comment
                    try:
                        if post_comment is not None and post_comment[0:1] != self._comment:
                            post_comment = "%s %s" % (self._comment,post_comment,)
                    except:
                        pass
                else:
                    pass

            else:
                _val = value

            _prefix = ""
            if iscomment is True:
                _prefix += self._comment
            if level > 0:
                _prefix += str_repeat(self._indent,level)

            if type(_val) == dict:

                # ORDER順に設定する
                orders = []
                try:
                    old_orders = _val[orders_key]['value']
                except:
                    old_orders = []

                for kk in old_orders:
                    if type(kk) is list:
                        orders.append(kk[0])
                    elif type(kk) is str:
                        orders.append(kk)

                for kk in list(_val.keys()):
                    if not kk in orders:
                        orders.append(kk)

                #for _k2,_v2 in _val.iteritems():
                for _k2 in orders:

                    if _k2 == orders_key:
                        continue
                    _v2 = _val[_k2]

                    sub_value = {}
                    sub_value[_k2] = _v2

                    try:
                        iscomment = sub_value[_k2]['comment']
                    except:
                        iscomment = False

                    try:
                        action = sub_value[_k2]['action']
                    except:
                        action = ""

                    if action == "delete":
                        continue

                    #try:
                    #    sub_value[_k2]['value'][1][0]
                    #    lines = lines + sub_value[_k2]['value'][1][0]
                    #except:
                    #    pass


                    is_sect = False
                    if _k in self.opt_multi and _k2 == _v2["value"][0]:
                        for _k3,_v3 in sub_value.items():
                            try:
                                iscomment3 = sub_value[_k3]['comment']
                            except:
                                iscomment3 = iscomment
                            try:
                                action3 = sub_value[_k3]['action']
                            except:
                                action3 = ""

                            _prefix = ""
                            if iscomment is True:
                                _prefix += self._comment
                            if level > 0:
                                _prefix += str_repeat(self._indent,level)
                            lines.append("%s%-18s%s%s" % (_prefix,_k,self._new_delim,_k2))

                    elif _k in self.opt_sect:
                        is_sect = True
                        _prefix = ""
                        if iscomment is True:
                            _prefix += self._comment
                        if level > 0:
                            _prefix += str_repeat(self._indent,level)
                        if _k2 == "":
                            lines.append("%s<%s>" % (_prefix,_k))
                        else:
                            lines.append("%s<%s \"%s\">" % (_prefix,_k,_k2))

                    new_level = level + 1
                    new_lines = self._value_to_lines(sub_value,level=new_level)

                    for _aline in new_lines:
                        _prefix2 = ""
                        if iscomment is True:
                            _prefix2 += self._comment
                        new_aline = "%s%s" % (_prefix2,_aline,)
                        new_aline = re.sub("^%s+" % self._comment,self._comment,new_aline)
                        lines.append(new_aline)
                    #lines = lines + new_lines

                    if is_sect is True:
                        lines.append("%s</%s>" % (_prefix,_k,))

            else:

                aline = ""
                if _k in self.opt_multi:
                    aline += "%s%-18s%s%s" % (_prefix,_k,self._new_delim,_val,)
                else:
                    if re.match("^[A-Z]+[a-z]",_k):
                        aline += "%s%-18s%s%s" % (_prefix,_k,self._new_delim,_val,)

                if post_comment is not None:
                    aline = "%s %s" % (aline,post_comment,)

                if aline != "":
                    lines.append(aline)

        return lines


    def write_conf(self,conf_arr={},dryrun=False):
        retval = True

        self.dop.addconf(self._module,conf_arr)
        orders_key = "%sORDERS" % (self._reserved_key_prefix,)
        eof_key    = "%sEOF"    % (self._reserved_key_prefix,)

        for _path,_v in conf_arr.items():

            if _path[0:1] != "/":
                continue

            lines = []
            try:
                _v['value']
            except:
                continue

            exclude_regex = "^%s[A-Z0-9\_]+$" % self._reserved_key_prefix

            # まずはオーダの順
            if self.dop.isset(self._module,[_path,orders_key]) is True:
                for _k2 in self.dop.get(self._module,[_path,orders_key]):
                    try:
                        if type(_k2) == str:
                            _k2 = [_k2]
                        _search_key = [_path] + _k2

                        is_opt_multi = False
                        if _k2[0] in self.opt_multi:
                            _tmp_conf = self.dop.get(self._module,_search_key)
                            # multiとsectがかぶったオプションの対応 strならmulti
                            if type(_tmp_conf[0]) == str:
                                is_opt_multi = True

                        if is_opt_multi is True:
                            _k2.pop()

                        new_lines = self._new_lines(_search_key,_k2)
                        lines = lines + new_lines
                        self.dop.unset(self._module,_search_key)
                    except:
                        pass

            # オーダにないものは最後に追加
            for _k2,_v2 in self.dop.get(self._module,[_path]).items():

                #if _k2 != orders_key:
                m = re.match(exclude_regex,_k2)
                if not m:
                    try:
                        if type(_k2) == str:
                            _k2 = [_k2]
                        _search_key = [_path] + _k2

                        if _k2[0] in self.opt_multi:
                            for _k3,_v3 in self.dop.get(self._module,_search_key).items():
                                _search_key.append(_k3)
                                new_lines = self._new_lines(_search_key,_k2)
                                lines = lines + new_lines
                        else:
                            new_lines = self._new_lines(_search_key,_k2)
                            lines = lines + new_lines

                    except:
                        pass


            # 最後のコメント用の処理
            if self._footer != "":
                if self.dop.isset(self._module,[_path,eof_key]) is False:
                    self.dop.cdp_set(self._module,[_path,eof_key],"",force=True)

                eof_val     = self.dop.get(self._module,[_path,eof_key])
                eof_action  = self.dop.action(self._module,[_path,eof_key])
                eof_comment = self.dop.comment(self._module,[_path,eof_key])
                try:
                    key = " %s - %s on %s" % (self._footer,self._module,time.strftime("%c",time.localtime()))
                    value = {}
                    value[key] = {}
                    value[key]["value"]   = eof_val
                    value[key]["action"]  = eof_action
                    value[key]["comment"] = eof_comment
                    self.set_new_delim(delim=" ")
                    lines = lines + self._value_to_lines(value)
                except:
                    pass

            if dryrun is False:
                if len(lines) > 0:
                    ConfigFile(_path).write("\n".join(lines) + "\n")
            else:
                print("%s -- filename: %s" % (self._comment,_path,))
                print("\n".join(lines))

        return retval

    def _new_lines(self,search_key,new_key):

        try:
            attrs = self.dop.get(self._module,search_key,with_attr=True)
            action    = attrs['action']
            iscomment = attrs['comment']
            val       = attrs['value']
        except:
            action    = self.dop.action(self._module,search_key)
            iscomment = self.dop.iscomment(self._module,search_key)
            val       = self.dop.get(self._module,search_key)
            pass

        #print val
        dop = DictOp()
        dop.addconf('__',{})
        if action == "delete":
            dop.add('__',new_key,val)
            dop.delete('__',new_key)
        elif action == "set":
            dop.set('__',new_key,val)
        else:
            dop.add('__',new_key,val)
        if iscomment is True:
            dop.comment('__',new_key)

        #preprint_r(dop.getconf('__'))
        new_lines = self._value_to_lines(dop.getconf('__'))
        #print "\n".join(new_lines)

        return new_lines

"""
"""
if __name__ == '__main__':
    """Testing
    """
    parser = xmlLikeConfParser()
    parser.set_source_file("/etc/collectd.conf")

    conf_arr = parser.read_conf()
    dop = DictOp()
    dop.addconf("parser",conf_arr)
    conf_arr = dop.getconf("parser")
    preprint_r(conf_arr)
    parser.write_conf(conf_arr,dryrun=True)
