# This module contains a wrapper around mod_python. The wrapper is designed to
# be as generic as possible, since we might eventually find something better to
# replace mod_python with.
from mod_python import apache, util, Session, Cookie
import cgi
from kodict import *
from kweb_lib import *

# This table maps HTTP status codes to mod_python codes.
KWEB_LIB_STATUS_TABLE = {
    KWEB_LIB_STATUS_OK : apache.OK,
    KWEB_LIB_STATUS_MOVED_TEMPORARILY : apache.HTTP_MOVED_TEMPORARILY,
    KWEB_LIB_STATUS_INTERNAL_ERROR : apache.HTTP_INTERNAL_SERVER_ERROR
}

# This class represents a file uploaded by the user. The 'name' field contains
# the name of the file provided by the browser of the user. The 'file' field
# contains an opened file-like object containing the data of the file.
class KWebFile(object):
    def __init__(self, filename, file):
        self.filename = filename
        self.file = file

    def __str__(self):
        return "<%s filename='%s'>" % ( self.__class__.__name__, self.filename )

# Mod_python framework wrapper.
class MpFramework(object):
    
    # Constructor of the mod_python framework object. It must be passed the
    # request object received from mod_python.
    def __init__(self, req):

        # Debugging level:
        # 0: debugging disabled.
        # 1: log only critical information.
        # 2: log informational messages.
        self.debug_level = 0
    
        # True if profiling is enabled. Enabling profiling also enables
        # debugging.
        self.profile_flag = False
        
        # Reference to the session.
        self.session = None
        
        # Reference to self.session.data, for ease of access.
        self.sd = None
        
        # If this value is not 'None', it overrides the HTTP connection type
        # value supplied by the user's browser.
        self.conn_type_override = None
        
        # Variables which are "global" to the request are stored in this
        # property store.
        self.gd = PropStore()
        
        # Request handler from mod_python.
        self.__req = req
        
        # FieldStorage instance from mod_python. It is important not to lose the
        # reference to this instance, otherwise the associated file objects
        # could get garbage-collected (at least this is the current hypothesis).
        self.__field_storage = util.FieldStorage(self.__req)
        
        # List of GET and POST variables extracted from the client's request. It
        # is legal to modify those variables as needed.
        self.__vars = odict()
        
        # List of files uploaded by the client.
        self.__files = {}
        
        # Dictionary of HTTP headers extracted from the client's request.
        self.__headers_in = {}
        
        # Ordered dictionary of HTTP headers to send to the client.
        self.__headers_out = odict()
        
        # Dictionary of cookies extracted from the client's request.
        self.__cookies_in = None
       
        # Ordered dictionary of HTTP cookies to send to the client.
        self.__cookies_out = odict()

        # HTTP status to send to the client.
        self.__http_status = None
        
        # Content type to send to the client.
        self.__content_type = None
        
        # Buffered data to send to the client.
        self.__buf_data = ""
        
        # True if the user has already written data to the client. In that case,
        # any buffered data or headers will not be written at the end of the
        # request.
        self.__data_written = False
        
        # If a redirect has been requested, this field contains the URL to
        # redirect to.
        self.__redirect_url = None
        
        # Set the default status and content type.
        self.setStatus(KWEB_LIB_STATUS_OK)
        self.setContentType("text/html")
        
    # HTTP status property (read/write).
    def getStatus(self):
        return self.__http_status
    def setStatus(self, x):
        self.__http_status = x
    status = property(getStatus, setStatus)

    # Content type property (read/write).
    def getContentType(self):
        return self.__content_type
    def setContentType(self, x):
        self.__content_type = x
    content_type = property(getContentType, setContentType)

    # Input headers property (read/write).
    def getHeadersIn(self):
        return self.__headers_in
    def setHeadersIn(self, x):
        self.__headers_in = x
    headers_in = property(getHeadersIn, setHeadersIn)

    # Output headers property (read/write).
    def getHeadersOut(self):
        return self.__headers_out
    def setHeadersOut(self, x):
        self.__headers_out = x
    def appendHeadersOut(self, key, value):
        # flush current value if any (needed so appened data is always last... (this is an odict and not a regular dict)
        if self.__headers_out.has_key(key):
            del self.__headers_out[key]
        # append new value
        self.__headers_out[key] = value
    headers_out = property(getHeadersOut, setHeadersOut)

    # Output cookies perperty (read/write)
    def getCookiesOut(self):
        return self.__cookies_out
    def setCookiesOut(self, x):
        self.__cookies_out = x
    def appendCookiesOut(self, key, value):
         # flush current value if any (needed so appened data is always last... (this is an odict and not a regular dict)
        if self.__cookies_out.has_key(key):
            del self.__cookies_out[key]
        # append new value
        self.__cookies_out[key] = value

    # Environment property (read-only). This is the environment returned by
    # mod_python.
    def getEnv(self):
        return self.__req.subprocess_env
    def setEnv(self, x):
        pass
    env = property(getEnv, setEnv)
    
    # This function must be called to process the client's request. 'func' is
    # the application callback function that will be called to process the
    # client's request. After 'func' has been called, this function will throw
    # one of the exceptions expected by mod_python.
    def use_handler(self, func):
        
        if self.profile_flag:
            self.profile("start of app handler")

        # Call the application callback function.
        func(self)

        if self.profile_flag:
            self.profile("end of app handler")

        # If a redirect has been requested, redirect now.
        if self.__redirect_url != None: util.redirect(self.__req, self.__redirect_url)
        
        # If no data has been written to the client yet, write any buffered
        # headers and data.
        if not self.__data_written:
            if self.__content_type: self.__req.content_type = self.__content_type
            self.__write_headers()
            self.__write_cookies()
            self.__req.write(self.__buf_data)

        if self.profile_flag:
            self.profile("end of mp handler")

        # Tell Apache the request has been handled successfully.
        raise apache.SERVER_RETURN, self.get_status_mod_python(self.__http_status)

    # This function must be called to initialize the state of this object from
    # mod_python. This should be called after use_handler() has been called.
    def init(self):
        
        # Parse the HTTP headers for variables and files.
        for field in self.__field_storage.list:
            
            # This is a normal variable.
            if str(type(field.file)) == "<type 'cStringIO.StringI'>" or \
                str(type(field.file)) == "<type 'cStringIO.StringO'>":
                    self.set_var(field.name, field.value)
                
            # This is a file.
            else:
                # Some browsers give a full path instead of a file name. Some
                # browsers give an encoded file name. Plan for those cases.
                # FIXME: is the explanation above and the code below correct?
                filename = field.filename
                filename = urllib.unquote_plus(filename) # unquote filename (it should be encoded like an url)
                filename = re.sub(r'\\+', '/', filename) # some OS use "\" for paths... replace '\' in '/'
                filename = os.path.basename(filename) # some browsers (IE) send full path.. rip path part and just get file name
                self.__files[field.name] = KWebFile(filename, field.file)
        
        # Store the HTTP headers.
        for key in self.__req.headers_in:
            self.__headers_in[key] = self.__req.headers_in[key]

        # Initialize the cookies.
        self.__cookies_in = Cookie.get_cookies(self.__req)
    
    # This method enables or disables debugging.
    def set_debug(self, level):
        self.debug_level = level

    # This method enables or disables profiling.
    def set_profile(self, enable_flag):
        self.profile_flag = enable_flag
        
        # Remember the time at which the request started.
        if enable_flag: self.__profile_startstamp = time.time()
    
    # This method stores the session specified in this object.
    def set_session(self, session):
        self.session = session
        self.sd = session.data

    # This method clears data from session without clearing the session
    def clear_session_data(self):
        self.session.clear_data()
        self.sd = self.session.data

    # This method calls debug() with a string indicating the time elapsed
    # since the query was started.
    def profile(self, comment):
        if self.profile_flag:
            t = time.time()
            self.debug(1, "profiling: %s (now: %f, elapsed: %f, query='%s')" \
                          % (comment, t, t - self.__profile_startstamp, str(self.cur_query())))
    
    # This method stores the data specified in the output buffer. The output
    # buffer will be written at the end of the request.
    def out(self, data, drop_existing=False):
        if drop_existing:
            self.__data = str(data)
        else:
            self.__buf_data += str(data)
    
    # This method logs the message specified in the Apache logs if the level
    # specified is lower or equal to the debugging level.
    def debug(self, level, msg):
        if level <= self.debug_level: self.__req.log_error("=DEBUG=> " + msg)

    # This method logs the message specified in the Apache logs
    def error(self, msg):
        self.__req.log_error("=ERROR=> " + msg)

    # This method logs the message specified in the Apache logs
    def log(self, msg):
        self.__req.log_error(msg)

    # This method writes the data specified to the client without buffering.
    def write(self, data):
        if not self.__data_written:
            self.__data_written = True
            if self.__content_type: self.__req.content_type = self.__content_type
            self.__write_headers()
            self.__write_cookies()
        self.__req.write(data)
    
    # This method adds a header to the output header list.
    def append_header_out(self, key, value):
        self.__headers_out[key] = value
        
    # This method writes the buffered headers to the client.
    def __write_headers(self):
        self.debug(2, "Output headers:")
        for key in self.__headers_out:
            self.debug(2, "Outputing header: %s ==> %s." % (key, self.__headers_out[key]))
            self.__req.headers_out[key] = self.__headers_out[key]

    # This method writes the buffered cookies to the client.
    def __write_cookies(self):
        self.debug(2, "Output cookies:")
        for key in self.__cookies_out:
            self.debug(2, "Outputing cookie: %s ==> %s." % (key, self.__cookies_out[key]))
            # This is wierd....
            Cookie.add_cookie(self.__req, self.__cookies_out[key])
            #self.__req.headers_out["Set-Cookie"] = self.__cookies_out[key]

    # This method redirects to a URL.
    def redirect(self, url, twice=False):
        if twice:
            # Redirecting twice can possibly fix some problems. FIXME.
            self.sd.redirect_twice = 1
        self.debug(2, "Redirecting from '%s' to '%s'." % ( self.build_url(), url ) )
        self.__write_headers()
        self.__write_cookies()
        self.profile("redirect: url='%s', twice='%s'" % (url, str(twice)))
        util.redirect(self.__req, url)
    
    # This method redirects to the current page.
    def redirect_self(self, twice=False):
        self.redirect(self.build_url(), twice)

    # This method redirects to a built URL.
    def redirect_build(self, **params):
        self.redirect(self.build_url(**params))

    # This method returns the server host
    def host(self):
        return self.__req.hostname

    # This method returns the URL path.
    def path(self):
        return self.__req.parsed_uri[6]

    # This method builds a new URL based on current URL and the provided
    # parameters.
    def build_url(self, conn_type=None, conn_hostname=None, conn_port=None, path=None, query=None):
        s = ''
        
        # Connection string: (http|https)://host[:port]
        if conn_type == None: conn_type = self.conn_type()
        s += conn_type + '://'
        
        if conn_hostname == None: conn_hostname = self.host()
        s += conn_hostname

        if conn_port == None: conn_port = self.__req.parsed_uri[5]
        if conn_port: s += ":" + str(conn_port)

        # Path.
        if path == None: path = self.__req.parsed_uri[6]
        if path:
            s += path
        else:
            s += "/"
        
        # GET query.
        if query == None: query = str(self.cur_query())
        if query: s += '?' + query

        return s

    # This method returns the current GET query, optionally with the session ID
    # appended.
    def cur_query(self, include_sid=True):
        # FIXME.
        #q = KWebVarEncoder(cgi.parse_qsl(self.env["QUERY_STRING"]))
        q = KWebVarEncoder(self.__vars)
        if include_sid and self.session != None: q["sid"] = self.session.sid
        return q

    # This method translates an HTTP status code to the mod_python equivalent.
    def get_status_mod_python(self, status=None):
        if status == None: status = self.__http_status
        if KWEB_LIB_STATUS_TABLE.has_key(status): return KWEB_LIB_STATUS_TABLE[status]
        return KWEB_LIB_STATUS_TABLE[KWEB_LIB_STATUS_INTERNAL_ERROR]
    
    # This method returns the value of the GET or POST variable specified. If
    # the variable does not exist, 'None' is returned. Files are not retrieved
    # with this method.
    def get_var(self, key):
        if self.__vars.has_key(key):
            return self.__vars[key]
        return None

    # This method sets the value of a variable. This can be used to simulate the
    # effect of a variable sent by the client's browser.
    def set_var(self, key, value):
        self.__vars[key] = value

    # This method deletes the value of a variable. This can be used to simulate the
    # effect of a variable not being sent by the client's browser
    def del_var(self, key):
        del self.__vars[key]

    # This method returns the dictionary containing the GET and POST variables.
    def get_vars(self):
        return self.__vars

    # This method returns the file object representing a file uploaded by the
    # client's browser, or 'None'.
    def get_file(self, key):
        if self.__files.has_key(key):
            return self.__files[key]
        return None

    # This method returns the dictionary containing the files uploaded by the
    # client's browser.
    def get_files(self):
        return self.__files

    # This method retrieves the value specified in the cookie sent by the
    # client's browser, or 'None'.
    def get_cookie_var(self, key):
        if self.__cookies_in.has_key(key):
            return self.__cookies_in[key]
        return None

    # This method returns the browser's connection type, either 'http' or
    # 'https'.
    def conn_type(self):
        # Use overriden value. 
        if self.conn_type_override != None: return self.conn_type_override
        
        # I read everywhere that SSL was enabled when
        # req.subprocess_env.has_key('HTTPS') was 'on' but I got ['on', 'on'].
        if self.__req.subprocess_env.has_key('HTTPS') and \
           (self.__req.subprocess_env['HTTPS'] == 'on' or self.__req.subprocess_env['HTTPS'].count('on') >= 1):
            return 'https'
        else:
            return 'http'
    
    # This method returns the session ID if it exists, otherwise this method
    # throws an exception.
    def get_sid(self):
        if self.session and self.session.sid != None: return self.session.sid
        raise Exception("no session ID currently exist")
    
    # This function returns a string defining the hidden input control containing
    # the session ID.
    def sid_input(self):
        return "<input id='sid' type='hidden' name='sid' value='%s'>\n" % (self.get_sid())
    
    
        
