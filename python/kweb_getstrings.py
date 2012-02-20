#!/usr/bin/env python

# Preliminary module to get web strings support.
# Will probably update to gettext later when we want multi-languages support.

import re

# local
import kweb_lib

# from kpython
import kdebug
import kgetstrings

# This function gets a translated and html-escaped string.
# If <allow_basic_html> is True, will allow some html tags to pass through: <b>, </b>, <p>, </p>, <i>, </i>,
# <nbsp> (which is not a real html tag by the way).
def get_html_escaped_string(strings, key, app=None, none_if_missing=False, allow_basic_html=False):
    kdebug.debug(1, "set_strings(key='%s', app='%s', none_if_missing='%s', allow_basic_html='%s'" % \
        ( key, str(app), str(none_if_missing), str(allow_basic_html) ), "kweb_getstrings" )

    # get the string
    tmpstr = kgetstrings.get_string(strings, key, app=app, none_if_missing=none_if_missing)
    if not tmpstr:
        return None

    # escape basic forbidden html characters (not entities)
    tmpstr = kweb_lib.html_text_escape(tmpstr)

    if allow_basic_html:
        # unescape some html tags that we allow in strings
        tmpstr = re.sub('&lt;nbsp&gt;', "&nbsp;", tmpstr) # special case -- convert <nbsp> (not a real tag) to &nbsp;
        tmpstr = re.sub('&lt;(\/?)(p|b|i)&gt;', "<\\1\\2>", tmpstr) # convert back <p>, </p>, <b>, </b>,  <i>, </i>

    return tmpstr


# Un-exhaustive tests
if __name__ == "__main__":
    strings = {}
    print get_html_escaped_string(strings, "lalala")
    print get_html_escaped_string(strings, "lalala", none_if_missing=True)

    strings = { "app1" : {"lala" : "La La<b>lala</b>''", "lili" : "Li Li"} }
    print get_html_escaped_string(strings, "lala", allow_basic_html=True)
    print get_html_escaped_string(strings, "lala", app="app1", allow_basic_html=True)

