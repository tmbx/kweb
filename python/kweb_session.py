# This module contains the session-management code.

import pickle

# From kpython package
from kpg import *
import kdebug # need to import this way - see kdebug

# This function validates a session id.
def is_sid_valid(sid):
    if re.match('^[a-zA-Z0-9]+$', sid): return True
    return False

# This class represents a web session with a user.
class KSession:
    
    # This constructor creates an empty session with no session ID and an empty
    # PropStore in the data field. The constructor takes a Postgres connection
    # to the session database as parameter.
    def __init__(self, conn):
        
        # Postgres connection used to retrieve/store the session.
        self.conn = conn

        # Init session informations and data
        self.clear()
    
    # This method (re-)inits session informations and data
    def clear(self):
        # Session ID, if any.
        self.sid = None

        # Session stamps
        self.creation_date = None
        self.last_read = None
        self.last_update = None

        # Data of the session.
        self.data = PropStore()

    # This method assigns an empty PropStore to the data field.
    def clear_data(self):
        # Data of the session.
        self.data = PropStore()

    # This method check if session is older than X seconds.
    def is_older(self, seconds):
        if not self.creation_date or time.time() < (self.creation_date + seconds):
            return False
        return True

    # This function retrieves the session data corresponding to the ID specified
    # from the database. If no such session data is found, false is returned.
    # Otherwise, the session data is unpickled and assigned to the data field,
    # the session ID field is updated, the session last_read field is updated in db,
    # and the function returns true.
    def load(self, sid):
        if not is_sid_valid(sid): raise Exception("Invalid session id: hex:'%s'" % ( sid.encode("hex") ) )
        self.clear()
        cur = exec_pg_query_rb_on_except(self.conn, 
                "SELECT creation_date, last_read, last_update, data FROM session WHERE id = %s" \
                % (escape_pg_string(sid)))
        row = cur.fetchone()

        if row == None:
            self.conn.commit()
            return 0

        now = int(time.time())
        cur = exec_pg_query_rb_on_except(self.conn,
                                       "UPDATE session SET last_read = %s WHERE id = %s" \
                                       % ( ntos(now), escape_pg_string(sid)))
        if cur.rowcount < 1:
            self.conn.rollback()
            raise Exception("Could not update session read stamp for session '%s'." % ( str(sid) ) )

        creation_date = row[0]
        last_read = row[1]
        last_update = row[2]
        data = pickle.loads(row[3].value)
        self.conn.commit()
        self.creation_date = creation_date
        self.last_read = last_read
        self.last_update = last_update
        self.data = data
        self.sid = sid
        return 1
    
    # This function saves the session in the Postgres database. If a session ID
    # is present, the session entry is updated in the database. This involves
    # updating the data of the session and setting the last update time to now.
    # Otherwise, the session is inserted in the database with a unique ID.
    def save(self):
        # Pickle the data.
        data_str = pickle.dumps(self.data) 

        # Try to insert the session three times, for the unlikely case where we
        # collide with another ID.
        if self.sid == None:
            attempt = 0
            
            while 1:
                sid = gen_random(20)
                
                try:
                    now = int(time.time())
                    cur = exec_pg_query_rb_on_except(self.conn,
                                        "INSERT INTO session (id, data, creation_date, last_update) VALUES " +\
                                        "(%s, %s, %s, %s)" \
                                        % (escape_pg_string(sid), escape_pg_bytea(data_str), ntos(now), ntos(now)))
                    self.conn.commit()
                 
                except:
                    attempt += 1
                    if attempt > 2: raise
                    continue
                
                self.sid = sid
                break
        
        # Update the entry. If the entry no longer exists, this is an error.
        else:
            now = int(time.time())
            cur = exec_pg_query_rb_on_except(self.conn, "UPDATE session SET data = %s, last_update = %s WHERE id = %s" \
                                           % (escape_pg_bytea(data_str), ntos(now), escape_pg_string(self.sid)))
            if cur.rowcount != 1:
                self.conn.commit()
                raise Exception("session no longer exists in database")
                
            self.conn.commit()

# This function opens the Postgres session connection if required.
def ksession_open_pg_conn(database="session"):
    global ksession_pg_conn
    
    # There is a cached connection open. Test if it works.
    if ksession_pg_conn != None:
        try:
            if ksession_pg_conn.inTransaction:
                kdebug.debug(1, "Cached session connection not clean... rolling previous transaction back.", "ksession")
                ksession_pg_conn.rollback()
            exec_pg_query_rb_on_except(ksession_pg_conn, "SELECT 1")
            ksession_pg_conn.rollback()
            kdebug.debug(2, "Cached session connection operational.", "ksession")
            return
        except Exception, e:
            kdebug.debug(2, "Cached session connection does not work, reopening.", "ksession")
            ksession_pg_conn = None

    # There is no current connection. Open a new one.
    else:
        kdebug.debug(2, "No session connection open, opening new one.", "ksession")
        
    try:
        ksession_pg_conn = open_pg_conn(database=database)
    except:
        ksession_pg_conn = None
        raise

# This function loads and creates session objects. If a session ID is specified,
# the function attempts to load this session. On failure, or if no session ID is
# specified, the function attempts to create a new session. If create_as_needed
# is false, however, the function throws an exception instead of creating a new
# session. On success, the session object is returned.
def ksession_get_session(sid=None, database='session', create_as_needed=1):

    # Open the session connection if required.
    ksession_open_pg_conn(database=database)
    
    # Create the session object.
    s = KSession(ksession_pg_conn)
    
    # The session possibly exists. Try to load it.
    if sid != None:
        if s.load(sid):
            kdebug.debug(2, "Session with ID %s loaded successfully." % (sid), "ksession")
            return s
            
        else:
            kdebug.debug(2, "Session with ID %s was not found in database." % (sid), "ksession")
     
    # We would have to create a new session, but we're not allowed to.
    if not create_as_needed: raise Exception("the user session does not exist")
    
    # Save and return the session.
    s.save()
    kdebug.debug(2, "Created new session with ID %s." % (s.sid), "ksession")
    return s

# Cached Postgres connection.
ksession_pg_conn = None



# non-exhaustive tests
if __name__ == "__main__":
    s = ksession_get_session()
    print "First sid: " + str(s.sid)
    s.data["lala"] = "baba"
    print "data set"
    print "data: " + str(s.data)
    s.save()

    print "Reloading same session"
    sid = s.sid
    print sid
    s = ksession_get_session(sid)
    print "Should be the same sid: " + str(s.sid)
    print s.sid
    print s.data["lala"]
    s.clear_data()
    s.save()

    s = ksession_get_session(s.sid)
    print s.sid
#    print s.data["lala"]
    s.data["lalalalala"] = {"lala" : "lili"}
    s.save()

    s = ksession_get_session(s.sid)
    print s.sid
    print s.data["lalalalala"]
 

    s = ksession_get_session()
    print s.sid



