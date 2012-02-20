# This module contains some web-related code common to all web interfaces.

import urllib, xml.sax.saxutils

# From kpython
import kodict
from kbase import *

# HTTP status codes to return to the user when his request has been processed.
KWEB_LIB_STATUS_OK = 200
KWEB_LIB_STATUS_MOVED_TEMPORARILY = 307
KWEB_LIB_STATUS_INTERNAL_ERROR = 500

# This class is used to encode a set of GET variables into a HTTP URL portion.
# For instance, if the dictionary contains the variables (foo,3) and
# (bar,hello), the resulting URL would be 'foo=3&bar=hello'.
class KWebVarEncoder(kodict.odict):
    def __str__(self):
        return urllib.urlencode(self.plist())
    def __repr__(self):
        return urllib.urlencode(self.plist())
                
# This function returns a properly HTML-escaped version of the string specified
# for an HTML input field. Note that the string returned is enclosed within
# single quotes.
def html_attribute_escape(s):
    return xml.sax.saxutils.quoteattr(s)
    
# This function returns a properly HTML-escaped version of a string for
# inclusion in free-standing HTML text.
def html_text_escape(s):
    l=[]
    # If the attribute is recognized, replace it, otherwise include it as-is.
    for c in s:
        l.append(html_text_escape_table.get(c, c))
    return "".join(l)

html_text_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&#39;",
    ">": "&gt;",
    "<": "&lt;",
}

# This function htmlizes text
def htmlize_text(s):
    s = s.replace("\n", "<br />\n")
    return s

# Error message exception class (an error message we generated ourselves that is
# meant to be displayed as-is to the user).
class ErrorMsg(Exception):
    def __init__(self, value): self.value = value
    def __str__(self): return self.value

# This function transforms a dict and returns a list of hidden form fields
def vars_to_hidden_fields(vars, indent_spaces=0):
    s = ""
    for k, v in vars.items():
        s += "%s<input type=\"hidden\" name=%s value=%s />\n" % ( (" " * indent_spaces), html_attribute_escape(k), html_attribute_escape(v) )
    return s

