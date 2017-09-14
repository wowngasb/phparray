from distutils.log import warn as printf

import re
import time
import os

SETTINGS = {}
LAST_COMPLETION_DEFAULT = {"needFix": False, "value": '', "region": ''}
LAST_COMPLETION = dict(LAST_COMPLETION_DEFAULT)

SINGLE_QUOTE_REG = re.compile(r"""(.*)('\s*@[s])""")
DOUBLE_QUOTES_REG = re.compile(r'''(.*)("\s*@[s])''')

def _try_array(arr_str):
    return str([i.strip() for i in arr_str.split(',') if i.strip()])

def _pre_find(strin, need, escape = '\\', newlines = set(['\r', '\n'])):
    slen = len(strin)
    start = slen - 1
    while start >= 0:
        char = strin[start]
        if char in newlines:
            return ''
        if char == need:
            if start > 0 and strin[start - 1] == escape:
                start -= 1
            else:
                return strin[start + 1:]
        start -= 1
    return ''

def test(prefix):
    prefix = prefix.split('\r')[-1].split('\n')[-1].strip()
    LAST_COMPLETION.update(LAST_COMPLETION_DEFAULT)
    location = len(prefix)

    reg_map = (('"', DOUBLE_QUOTES_REG), ("'", SINGLE_QUOTE_REG))
    for quote, reg in reg_map:
        tmp = reg.match(prefix)
        if not tmp:
            continue
        tmp_g = tmp.groups()
        arr_str = _pre_find(tmp_g[0], quote)
        start = location - len(arr_str) - len(tmp_g[1]) - 1
        value = _try_array(arr_str) if arr_str else ''
        if not value:
            break

        LAST_COMPLETION["needFix"] = True
        LAST_COMPLETION["value"] = value
        LAST_COMPLETION["region"] = (start, location)

    print(LAST_COMPLETION)
    if LAST_COMPLETION["needFix"]:
        v = LAST_COMPLETION["value"]
        s, e = LAST_COMPLETION["region"]
        print(prefix[:s] + v)

def main():
    prefix = r''' $tmp = ["abc",  'a, "b\'", c' @s'''
    test(prefix)

    prefix = r''' $tmp = ["abc",
'a, b, c' @s'''
    test(prefix)

    prefix = r''' $tmp = ["abc",
"a, b, c" @s'''
    test(prefix)

    prefix = r''' $tmp = ["abc",  "a, b, c" @s'''
    test(prefix)
    exit(0)

if __name__ == '__main__':
    # main()
    pass

import sublime
import sublime_plugin

def plugin_loaded():
    init_settings()

def init_settings():
    get_settings()
    sublime.load_settings('phparray.sublime-settings').add_on_change('get_settings', get_settings)

def get_settings():
    settings = sublime.load_settings('phparray.sublime-settings')
    SETTINGS['available_file_types'] = settings.get('available_file_types', ['.php', '.html'])

def get_setting(view, key):
    return view.settings().get(key, SETTINGS[key]);

class PhpArrayEventListener(sublime_plugin.EventListener):
    def on_text_command(self, view, name, args):
        if name == 'commit_completion':
            print('on_text_command', name, args)
            if LAST_COMPLETION.get('needFix', False):
                LAST_COMPLETION.update(LAST_COMPLETION_DEFAULT)
                return ('pass_php_array', None)
            #view.run_command('replace_php_array')
        return None

    def on_query_completions(self, view, prefix, locations):
        print('phparray start {0}, {1}'.format(prefix, locations))
        # only works on specific file types
        fileName, fileExtension = os.path.splitext(view.file_name())
        if not fileExtension.lower() in get_setting(view, 'available_file_types'):
            return []

        LAST_COMPLETION.update(LAST_COMPLETION_DEFAULT)
        location = locations[0]

        lineLocation = view.line(location)
        line = view.substr(sublime.Region(lineLocation.a, location))
        print('phparray try {0}, ({1},{2})'.format(line, lineLocation.a, location))

        if line[-2:] != '@s':
            return []

        reg_map = (('"', DOUBLE_QUOTES_REG), ("'", SINGLE_QUOTE_REG))
        for quote, reg in reg_map:
            tmp = reg.match(line)
            if not tmp:
                continue
            tmp_g = tmp.groups()
            arr_str = _pre_find(tmp_g[0], quote)
            start = location - len(arr_str) - len(tmp_g[1]) - 1
            value = _try_array(arr_str) if arr_str else ''
            if not value:
                break

            LAST_COMPLETION["needFix"] = True
            LAST_COMPLETION["value"] = value
            LAST_COMPLETION["region"] = sublime.Region(start, location)
            print(LAST_COMPLETION)
            return [('str -> array', value)]

        return []

class ReplacePhpArrayCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if not LAST_COMPLETION.get('needFix', False):
            return

        value = LAST_COMPLETION.get('value', '')
        region = LAST_COMPLETION.get('region', '')
        tmp = self.view.substr(region)
        print("tmp:{0}, replace:{1}".format(tmp, value))
        self.view.replace(edit, region, value)
        self.view.end_edit(edit)

class PassPhpArrayCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        pass