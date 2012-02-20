# Copyright (C) 2008-2012 Opersys inc., All rights reserved.

"""
Forms helpers
"""

import sys

# kpython lib
from kodict import *
import kdebug # need to import this module this way so it is global to all modules
from koptions import *
from kvalues import *
from kweb_lib import *
from kfilter import *

"""
# yet unported ruby code
def validate_datetime():

    valuesspecs = [ { "year" => { "min" => 2007, "max" => 9999 } },
                                                { "month" => { "min" => 1, "max" => 12 } },
                                                { "day" => { "min" => 1, "max" => 31 } },
                                                { "hour" => { "min" => 0, "max" => 24 } },
                                                { "min" => { "min" => 0, "max" => 59 } },
                                                { "sec" => { "min" => 0, "max" => 59 } } ]
                for specshash in valuesspecs.each # use array of hashes to keep order
                    for name,specs in specshash.each
                        var[name] = 0
                        tmpvalue = get_hash_var(input_values, [ idfield, name ])
                        if tmpvalue.None? || tmpvalue.to_s.length == 0:
                            form.error = True
                            field.error_required = True
                            field.errors.push(GTEH_("framework.field.error.must_be_filled_name") % name)
                        else:
                            begin
                                tmpvalue = var[name] = tmpvalue.to_i
                                if tmpvalue < specs["min"] || tmpvalue > specs["max"]:
                                    form.error = True
                                    field.errors.push(GTEH_("framework.field.error.invalid_value_name") % name)
                                
                            rescue
                                form.error = True
                                field.errors.push(GTEH_("framework.field.error.invalid_value_name") % name)
"""

class Forms:
    """
    Forms container
    """

    def __init__(self):
        self.forms = odict() # ordered dict
    
    def append_form(self, form):
        self.forms[form.id] = form
        return form

    def fill_form(self, id, input_values):
        # Find form
        try:
            form = self.forms[id]
        except KeyError, e:
            raise Exception("Non-existing form: '%s'" % ( str(id)) )

        # Fill form
        form.fill(input_values)


class Form:
    """
    Form (Field container)
    """

    def __init__(self, id, show=True, read_only=False, show_required_notice=True, anchor=None, 
                 show_legend=True, show_title=False):
        # Form ID - string list
        self.notices = []
        self.confirmations = []

        self.id = KStringValue(value=id, allow_none=False).value
   
        self.fields = odict() # ordered dictionary

        self.filled = False

        self.show = show

        self.read_only = read_only

        self.show_required_notice = show_required_notice

        self.anchor = anchor

        self.show_legend = show_legend

        self.show_title = show_title

    def append_field(self, field):
        self.fields[field.id] = field
        field.set_form_id(self.id)
        return field

    # yields each field with some infos added
    def each_field(self):
        count = 0
        total = len(self.fields)
        first = True
        for id, field in self.fields.items():
            if field.counts == True: # count and set those options for visible fields only
                count += 1

                field.first = (count == 1)
                field.odd = ((count % 2) == 1)
                field.even = ((count % 2) == 0)
                field.last = (count == total)
                field.index = count - 1
                
            yield field

    # fill form
    def fill(self, input_values):
        self.filled = True
        for field in self.fields.values():
            if isinstance(field, RadioButtonField):
                kdebug.debug(4, "Filling RadioButtonField field '%s' with values '%s'" % ( field.id, input_values ), 
		    "kweb_forms" )
                field.fill(input_values)
            else:
                if input_values.has_key(field.reference):
                    kdebug.debug(4, "Filling field '%s' with value '%s'" % ( field.id, input_values[field.reference] ), 
			"kweb_forms" )
                    field.fill(input_values[field.reference])
                else:
                    kdebug.debug(4, "Filling field '%s' with None (not sent)." % ( field.id ), "kweb_forms" )
                    field.fill(None)

            if isinstance(field, TextField) and field.verification_field_id:
                if self.fields[field.verification_field_id].value != field.value:
                    field.add_validation_exception(
			ValidationVerificationFieldException())

    # not used finally
    #def clear(self):
    #    self.confirmations = []
    #    self.notices = []
    #    self.filled = False
    #    for field in self.fields.values():
    #        field.clear()

    def valid(self):
        for field in self.fields.values():
            if not field.valid:
                return False
        return True

    def localize_validation_exceptions(self, d):
        for field in self.fields.values():
            field.localize_validation_exceptions(d)

class ValidationInvalidChoiceException(kfilter.ValidationException):
    pass

class ValidationVerificationFieldException(kfilter.ValidationException):
    pass

# Form field class
# override me
# Web applications are subject to a lot of quick changes... this class might look weird but it saves a lot
# of debugging by completely validating options passed through it (or the sub-classes)
class GenericField(Options):
    def __init__(self, id, **options):
        self.hidden = False
        self.filled = False
        self.validation_exceptions = []

        # store options if not already stored by a sub-class
        self.store_options(options)

        # Field ID - string list
        self.id = KStringValue(value=id, allow_none=False).value
        #self.id_str = recursive_string_list_to_string(self.id)

        # needed for debug (__str__)
        self._data = None

        kdebug.debug(3, "New instance of class '%s'" % ( str(self.__class__.__name__) ), "kweb_forms" )

        # FIXME - choose a better name, ...
        # Form.each_field behaves differently if counts is true or false
        self.counts = True

        # store options temporarily
        self.options = options

        # form id
        self.form_id = KStringValue(value=self.get_option("form_id", default_value="")).value

        # filters
        self.pre_filter_callables = self.get_option("pre_filter_callables", default_value=[])
        self.post_filter_callables = self.get_option("post_filter_callables", default_value=[])

        # field boolean options
        self.required = KBoolValue(value=self.get_option("required", default_value=False)).value
        self.force_value = KBoolValue(value=self.get_option("force_value", default_value=False)).value
        self.enabled = KBoolValue(value=self.get_option("enabled", default_value=True)).value
        self.autofocus = KBoolValue(value=self.get_option("autofocus", default_value=False)).value

        # Field reference (any type) - reference to anything
        self.reference = KStringValue(value=self.get_option("reference"), allow_none=False).value

        # Field classe(s) (string or list of strings)
        self.classes = KStringListValue(value=self.get_option("classes"), allow_none=True).value
        
        # Field tags (ordered dict of key/values)
        self.other_attributes = KStringDictValue(value=self.get_option("other_attributes"), allow_none=True).value

        self._data = KValue(value=self.get_option("value"),
                                    allow_none=(not self.required), raise_on_exception=False,
                                    pre_filter_callables=self.pre_filter_callables,
                                    post_filter_callables=self.post_filter_callables)

    # Set form id when needed
    def set_form_id(self, id):
        self.form_id = KStringValue(value=id, allow_none=False).value

    # Get unique id
    def _get_fid(self):
        if len(self.form_id):
            return self.form_id + "." + self.id
        return self.id
    fid = property(_get_fid)

    # Get unique id - suitable for html
    def _get_fid_html(self):
        if len(self.form_id):
            return self.form_id + "-" + self.id
        return self.id
    fid_html = property(_get_fid_html)


    # TODO: check why properties setters work with kvalues but don't work when using kvalues from fields
    def get_value(self):
        return self._data.value

    # fill the field.. get exceptions back
    def fill(self, value):
        self.filled = True
        if not self.force_value:
            self._data.set_value(value)
        self.validation_exceptions = self._data.validation_exceptions

    # set data only.. do not get validation exceptions back
    def set_value(self, value):
        self._data.set_value(value)
    value = property(get_value)

    def get_str_value(self):
        if self._data.value != None:
            return str(self._data.value)
        return ""
    str_value = property(get_str_value)

    def get_valid(self):
        # return wheither field value is valid or not
        if len(self.validation_exceptions) == 0:
            return True
        return False
    valid = property(get_valid)

    def add_validation_exception(self, e):
        self.validation_exceptions += [e]

    def localize_validation_exceptions(self, d):
        kdebug.debug(5, "Localizing messages for validation exceptions.", "kweb_forms" )
        for e in self.validation_exceptions:
            if d.has_key(e.classname()):
                e.message = d[e.classname()]
                kdebug.debug(6, "Found message id for for exception class '%s: '%s'." % ( e.classname(), d[e.classname()] ), "kweb_forms" )
            else:
                kdebug.debug(6, "Could not find local message for exception class '%s'." % ( e.classname() ), "kweb_forms" )

    def clear(self):
        self.set_value("")
        self.validation_exceptions = []

    def __str__(self):
        if self._data:
            return "<class '%s' id='%s' value='%s' valid='%s' validation_exceptions='%s'>" % \
                (
                    str(self.__class__.__name__), 
                    str(self.id),
                    str(self.value),
                    str(self.valid),
                    str(self.validation_exceptions)
                )
        else:
            return "<class '%s', id '%s'>" % ( str(self.__class__.__name__), str(self.id) )

    def _attr_to_string(self, k, v):
        return ' %s=%s' % ( k, html_attribute_escape(v) )

    def _attributes_string(self, attributes=None):
        s = ''
        if self.classes and len(self.classes):
            s += self._attr_to_string("class", ' '.join(self.classes))
        if self.other_attributes and len(self.other_attributes):
            for k, v in self.other_attributes:
                s += self._attr_to_string(k, v)
        return s
        

        
class TextField(GenericField):
    def __init__(self, id, **options):
        # store options if not already stored by a sub-class
        self.store_options(options)

        # field integer options
        self.size = KIntValue(value=self.get_option("size"), allow_none=True).value

        # Min and max length of text
        self.min_length = KIntValue(value=self.get_option("min_length"), allow_none=True).value
        self.max_length = KIntValue(value=self.get_option("max_length"), allow_none=True).value

        # If set: checks if the same value as the field referenced
        # Mostly used for password verification
        self.verification_field_id = KValue(value=self.get_option("verification_field_id"), allow_none=True).value

        # super!
        super(TextField, self).__init__(id, **options)

        kdebug.debug(1, "allow none: %s, required: %s" % ( str((not self.required)), str(self.required) ), "kweb_forms" )

        self._data = KStringValue(value=self.get_option("value"),
                                    allow_none=(not self.required), raise_on_exception=False,
                                    min_length=self.min_length, max_length=self.max_length,
                                    pre_filter_callables=[filter_none_to_empty_str] + self.pre_filter_callables,
                                    post_filter_callables=self.post_filter_callables)

    def html_output(self):
        return '<input type="text" id=%s name=%s%s value=%s />' % \
            ( html_attribute_escape(self.fid_html), html_attribute_escape(self.id),
              self._attributes_string(), html_attribute_escape(self.str_value) )

class PasswordTextField(TextField):
    def __init__(self, id, **options):
        # super!
        super(PasswordTextField, self).__init__(id, **options)

    def html_output(self):
        return '<input type="password" id=%s name=%s%s value=%s />' % \
            ( html_attribute_escape(self.fid_html), html_attribute_escape(self.id),
              self._attributes_string(), html_attribute_escape(self.str_value) )

class HiddenTextField(TextField):
    def __init__(self, id, **options):
        # super!
        super(HiddenTextField, self).__init__(id, **options)
        self.hidden = True


    def html_output(self):
        return '<input type="hidden" id=%s name=%s%s value=%s />' % \
            ( html_attribute_escape(self.fid_html), html_attribute_escape(self.id),
              self._attributes_string(), html_attribute_escape(self.str_value) )

class TextAreaField(TextField):
    def __init__(self, id, **options):
        # store options if not already stored by a sub-class
        self.store_options(options)

        # Rows and columns of textarea field
        self.cols = KIntValue(value=self.get_option("cols"), allow_none=True).value
        self.rows = KIntValue(value=self.get_option("rows"), allow_none=True).value

        # Min and max length of text
        self.min_length = KIntValue(value=self.get_option("min_length"), allow_none=True).value
        self.max_length = KIntValue(value=self.get_option("max_length"), allow_none=True).value

        # super!
        super(TextAreaField, self).__init__(id, **options)

        self._data = KStringValue(value=self.get_option("value"),
                                    allow_none=(not self.required), raise_on_exception=False,
                                    min_length=self.min_length, max_length=self.max_length,
                                    pre_filter_callables=[filter_none_to_empty_str] + self.pre_filter_callables,
                                    post_filter_callables=self.post_filter_callables)

    def _attributes_string(self):
        s = super(TextAreaField, self)._attributes_string()
        if self.cols:
            s += self._attr_to_string("cols", self.cols)
        if self.rows:
            s ++ self._attr_to_string("rows", self.rows)
        return s

    def html_output(self):
        return '<textarea id=%s name=%s%s>%s</textarea>' % \
                ( html_attribute_escape(self.fid_html), html_attribute_escape(self.id), 
                  self._attributes_string(), html_attribute_escape(self.str_value) )

class SelectField(GenericField):
    def __init__(self, id, **options):
        # store options if not already stored by a sub-class
        self.store_options(options)

        # field options with no special type
        # use odict() value to keep ordering
        self.choices = KStringDictValue(value=self.get_option("choices"), allow_none=False).value

        # super!
        super(SelectField, self).__init__(id, **options)

        self._data = KStringValue(value=self.get_option("value"),
                                     allow_none=(not self.required), raise_on_exception=False,
                                     pre_filter_callables=self.pre_filter_callables,
                                     post_filter_callables=[self.filter_choices]+self.post_filter_callables)
        # FIXME - validation must match one if the options

    # FIXME
    def filter_choices(self, value):
        kdebug.debug(4, "filter_choices: input value='%s'" % ( str(value) ), "kweb_forms" )

        if not value in self.choices.keys():
            return FilterResult(value=value, validation_exceptions=[ValidationInvalidChoiceException()], continue_filtering=False)

        return FilterResult(value=value)

    def html_output(self):
       s = '<select id=%s name=%s%s>\n' % \
                ( html_attribute_escape(self.fid_html), html_attribute_escape(self.id), self._attributes_string() )
       for k, v in self.choices.items():
           kdebug.debug(1, "DEBUG: '%s' -- '%s'" % ( str(self._data.value), str(k) ), "kweb_forms" )
           if str(self._data.value) == str(k):
               s += '<option value=%s selected>%s</option>\n' % ( html_attribute_escape(k), html_text_escape(v) )
           else:
               s += '<option value=%s>%s</option>\n' % ( html_attribute_escape(k), html_text_escape(v) )

       s += "</option>\n"
       return s

class CheckBoxField(GenericField):
    def __init__(self, id, **options):
        # Commented... no custom attribute.. will be done in parent class
        # store options if not already stored by a sub-class
        #self.store_options(options)

        # super!
        super(CheckBoxField, self).__init__(id, **options)

        # don't use KBoolValue because we need None converted to false...
        # (by choice and because None values do not reach class filter)
        # so, we use a custom pre-filter
        self._data =  KValue(value=self.get_option("value"), allow_none=True, raise_on_exception=False,
                                    pre_filter_callables=[kfilter.filter_booleanize_none] + self.pre_filter_callables,
                                    post_filter_callables=self.post_filter_callables)

    def html_output(self):
        if self.value:
            return '<input type="checkbox" id=%s name=%s%s checked />' % \
                ( html_attribute_escape(self.fid_html), html_attribute_escape(self.id), self._attributes_string() )
        else:
            return '<input type="checkbox" id=%s name=%s%s />' % \
                ( html_attribute_escape(self.fid_html), html_attribute_escape(self.id), self._attributes_string() )

class RadioButtonField(GenericField):
    def __init__(self, id, **options):
        # store options if not already stored by a sub-class
        self.store_options(options)

        # field options with no special type
        # use odict() value to keep ordering
        self.choices = KStringDictValue(value=self.get_option("choices"), allow_none=False).value

        # separater between choices
        self.choices_separator = KStringValue(value=self.get_option("choices", default_value="<br />")).value

        # super!
        super(RadioButtonField, self).__init__(id, **options)

        self._data = KStringValue(value=self.get_option("value"), allow_none=(not self.required),
                                  raise_on_exception=False,
                                  pre_filter_callables=self.pre_filter_callables,
                                  post_filter_callables=[self.filter_choices] + self.post_filter_callables)

    # FIXME
    def filter_choices(self, value):
        kdebug.debug(4, "filter_choices: input value='%s'" % ( str(value) ), "kweb_forms" )

        if not value in self.choices.keys():
            return FilterResult(value=value, validation_exceptions=[ValidationInvalidChoiceException()], continue_filtering=False)

        return FilterResult(value=value)

    def html_output(self):
        i = 0
        l = len(self.choices)
        for k, v in self.choices.items():
            i += 1
            if l >= 1 and (i == 1 or i == l - 1):
                s += self.choices_separator
            if self.value == k:
                s += '<input type="radio"id=%s name=%s%s value=%s checked /> %s' % \
                        ( html_attribute_escape(self.fid_html), html_attribute_escape(k), html_text_escape(v) )
            else:
                s += '<input type="radio"id=%s name=%s%s value=%s /> %s' % \
                        ( html_attribute_escape(self.fid_html), html_attribute_escape(self.id),
                          html_attribute_escape(k), html_text_escape(v) )
        return s


# non-exhaustive tests
if __name__ == "__main__":
    import sys

    #kdebug.set_debug_level(9, "kweb_forms")
    #kdebug.set_debug_level(9, "kfilter")
    #kdebug.set_debug_level(9, "kvalues")

    forms = Forms()
    form = forms.append_form(Form("basic_setup"))
    form.append_field(TextField("username", reference="username", required=True))
    form.append_field(TextField("password", reference="password", required=True))

    forms.forms["basic_setup"].fill({"username" : "gdfgdfg"}) #, "password" : None})
    for field in forms.forms["basic_setup"].each_field():
        print str(field)
        print field.html_output()


    def filter_test1(value):
        return FilterResult(value=value*3, validation_exceptions=[], continue_filtering=True)


    test_field = TextField("lala",
        value="boumboum", 
        pre_filter_callables=[filter_test1])
    print str(test_field)
    print test_field.html_output()
    print "\n"
 
    test_field.fill(544535)
    print str(test_field)
    print test_field.html_output()
    print "\n"

    test_field.fill("hello dear")
    print str(test_field)
    print test_field.html_output()
    print "\n"

    test_field.fill(6666666)
    print str(test_field)
    print test_field.html_output()
    print "\n"

    test_field = TextField("lala",
        value="boumboum", 
        required=True)
    print str(test_field)
    print test_field.html_output()
    print "\n"
 
    test_field.fill(None)
    print str(test_field)
    print test_field.html_output()
    print "\n"


