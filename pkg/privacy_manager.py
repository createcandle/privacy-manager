"""Power Settings API handler."""


import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import json
from time import sleep
import sqlite3
import requests
import datetime
import functools
import subprocess

try:
    from gateway_addon import APIHandler, APIResponse
    #print("succesfully loaded APIHandler and APIResponse from gateway_addon")
except:
    print("Import APIHandler and APIResponse from gateway_addon failed. Use at least WebThings Gateway version 0.10")
    sys.exit(1)
    
try:
    from gateway_addon import Database
except:
    print("Gateway not loaded?!")
    sys.exit(1)

print = functools.partial(print, flush=True)



_TIMEOUT = 3

_CONFIG_PATHS = [
    os.path.join(os.path.expanduser('~'), '.webthings', 'config'),
]

if 'WEBTHINGS_HOME' in os.environ:
    _CONFIG_PATHS.insert(0, os.path.join(os.environ['WEBTHINGS_HOME'], 'config'))



class PrivacyManagerAPIHandler(APIHandler):
    """Power settings API handler."""

    def __init__(self, verbose=False):
        """Initialize the object."""
        #print("INSIDE API HANDLER INIT")

        self.addon_name = 'privacy-manager'
        self.server = 'http://127.0.0.1:8080'
        self.DEV = False
        self.DEBUG = False
            
        self.things = [] # Holds all the things, updated via the API. Used to display a nicer thing name instead of the technical internal ID.
        self.data_types_lookup_table = {}
        
        
        try:
            manifest_fname = os.path.join(
                os.path.dirname(__file__),
                '..',
                'manifest.json'
            )

            with open(manifest_fname, 'rt') as f:
                manifest = json.load(f)

            APIHandler.__init__(self, manifest['id'])
            self.manager_proxy.add_api_handler(self)
            

            # LOAD CONFIG
            try:
                self.add_from_config()
            except Exception as ex:
                print("Error loading config: " + str(ex))

            
            if self.DEBUG:
                print("self.manager_proxy = " + str(self.manager_proxy))
                print("Created new API HANDLER: " + str(manifest['id']))
        except Exception as e:
            print("Failed to init UX extension API handler: " + str(e))
        
        try:
            #self.addon_path = os.path.join(os.path.expanduser('~'), '.webthings', 'addons', 'privacy-manager')
            self.addon_path =  os.path.join(self.user_profile['addonsDir'], self.addon_name)
            self.log_dir_path = os.path.join(self.user_profile['baseDir'], 'log')
            self.log_db_path = os.path.join(self.log_dir_path, 'logs.sqlite3')
            
        except Exception as e:
            print("Failed to further init UX extension API handler: " + str(e))
            
        # Respond to gateway version
        try:
            if self.DEBUG:
                print(self.gateway_version)
        except:
            print("self.gateway_version did not exist")
            
        while(True):
            sleep(1)
        



    # Read the settings from the add-on settings page
    def add_from_config(self):
        """Attempt to read config data."""
        try:
            database = Database('privacy-manager')
            if not database.open():
                print("Could not open settings database")
                return
            
            config = database.load_config()
            database.close()
            
        except:
            print("Error! Failed to open settings database.")
        
        if not config:
            print("Error loading config from database")
            return
        
        if self.DEV:
            print(str(config))

        if 'Debugging' in config:
            self.DEBUG = bool(config['Debugging'])
            if self.DEBUG:
                print("-Debugging preference was in config: " + str(self.DEBUG))



    def handle_request(self, request):
        """
        Handle a new API request for this handler.

        request -- APIRequest object
        """
        
        try:
        
            if request.method != 'POST':
                return APIResponse(status=404)
            
            if request.path == '/init' or request.path == '/get_property_data' or request.path == '/point_change_value' or request.path == '/point_delete' or request.path == '/internal_logs':

                try:
                    
                    if request.path == '/init':
                        
                        # Get the list of properties that are being logged
                        try:
                            data = self.get_init_data()
                            if isinstance(data, str):
                                state = 'error'
                            else:
                                state = 'ok'
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : state, 'data' : data}),
                            )
                        except Exception as ex:
                            print("Error getting init data: " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps("Error while getting thing data: " + str(ex)),
                            )
                            
                            
                    
                    elif request.path == '/get_property_data':
                        try:
                            target_data_type = self.data_types_lookup_table[int(request.body['property_id'])]
                            print("target data type from internal lookup table: " + str(target_data_type))
                            data = self.get_property_data( str(request.body['property_id']), target_data_type )
                            if isinstance(data, str):
                                state = 'error'
                            else:
                                state = 'ok'
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : state, 'data' : data}),
                            )
                        except Exception as ex:
                            print("Error getting thing data: " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps("Error while getting thing data: " + str(ex)),
                            )
                            
                            
                    elif request.path == '/point_change_value':
                        try:
                            data = []
                            target_data_type = self.data_types_lookup_table[int(request.body['property_id'])]
                            print("target data type from internal lookup table: " + str(target_data_type))
                            # action, data_type, property_id, new_value, old_date, new_date
                            data = self.point_change_value( str(request.body['action']), target_data_type, str(request.body['property_id']), str(request.body['new_value']), str(request.body['old_date']), str(request.body['new_date']) )
                            if isinstance(data, str):
                                state = 'error'
                            else:
                                state = 'ok'
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : state, 'data' : data}),
                            )
                        except Exception as ex:
                            print("Error getting thing data: " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps("Error while changing point: " + str(ex)),
                            )
                            
                            
                            
                            
                    elif request.path == '/point_delete':
                        print("POINT DELETE CALLED")
                        try:
                            data = []
                            
                            target_data_type = self.data_types_lookup_table[int(request.body['property_id'])]
                            print("target data type from internal lookup table: " + str(target_data_type))
                            
                            data = self.point_delete(str(request.body['property_id']), target_data_type, str(request.body['start_date']), str(request.body['end_date']) ) #new_value,date,property_id
                            if isinstance(data, str):
                                state = 'error'
                            else:
                                state = 'ok'
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : state, 'data' : data}),
                            )
                        except Exception as ex:
                            print("Error deleting point(s): " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps("Error while deleting point(s): " + str(ex)),
                            )
                            
                            
                        
                        
                    elif request.path == '/internal_logs':
                        print("INTERNAL LOGS CALLED")
                        try:
                            data = []
                               
                            action = "get"
                            filename = "all"
                            try:
                                filename = str(request.body['filename']) 
                            except:
                                print("No specific filename provided")
                            try:
                                action = str(request.body['action']) 
                            except:
                                print("No specific action provided, will read data.")
                               
                            data = self.internal_logs(action, filename)
                            if isinstance(data, str):
                                state = 'error'
                            else:
                                state = 'ok'
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : state, 'data' : data}),
                            )
                        except Exception as ex:
                            print("Error deleting point(s): " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps("Error while getting logs data: " + str(ex)),
                            )
                        
                        
                    else:
                        return APIResponse(
                          status=500,
                          content_type='application/json',
                          content=json.dumps("API error"),
                        )
                        
                        
                except Exception as ex:
                    print(str(ex))
                    return APIResponse(
                      status=500,
                      content_type='application/json',
                      content=json.dumps("Error"),
                    )
                    
            else:
                return APIResponse(status=404)
                
        except Exception as e:
            print("Failed to handle UX extension API request: " + str(e))
            return APIResponse(
              status=500,
              content_type='application/json',
              content=json.dumps("API Error"),
            )
        



    # INIT
    def get_init_data(self):
        if self.DEBUG:
            print("Getting the initialisation data")
        
        try:
            db = sqlite3.connect(self.log_db_path)
        except Exception as e:
            print("Error opening log file: " + str(e))
            return "Error opening log file: " + str(e)
            
        # Get list of properties that are being logged from database
        try:
            result = []
            cursor = db.cursor()
            cursor.execute("SELECT id,descr,maxAge FROM metricIds")
            all_rows = cursor.fetchall()
            #if self.DEBUG:
            #print(str(all_rows));
            for row in all_rows:
                
                # Get human readable title, if it's available.
                current_title = str(row[0])
                data_type = "none"
                try:
                    cursor.execute("SELECT value FROM metricsNumber WHERE id=?", (row[0],))
                    data_check = cursor.fetchall()
                    if len(data_check) > 0:
                        data_type = "metricsNumber"
                        self.data_types_lookup_table[row[0]] = 'metricsNumber'
                        if self.DEBUG:
                            print("Data type for this log is Number")
                    else:
                        try:
                            cursor.execute("SELECT value FROM metricsBoolean WHERE id=?", (row[0],))
                            data_check = cursor.fetchall()
                            if len(data_check) > 0:
                                data_type = "metricsBoolean"
                                self.data_types_lookup_table[row[0]] = 'metricsBoolean'
                                if self.DEBUG:
                                    print("Data type for this log is Boolean")
                            else:
                                print("Datatype also wasn't boolean. Must be other?")
                                # TODO here support for "other" can be added later, if necessary
                        except Exception as ex:
                            print("Error querying if boolean data exists for this item: " + str(ex))

                except Exception as ex:
                    print("Error getting test data to determine data type: " + str(ex))
                    
                #print("data_type = " + str(data_type))
                result.append( {'id':row[0],'name':row[1], 'data_type':data_type} )
                
            db.close()
            return result
    
        except Exception as e:
            print("Init: Error reading data: " + str(e))
            try:
                db.close()
            except:
                pass
            return "Init: general error reading data: " + str(e)



    # GET ALL DATA FOR A SINGLE THING
    def get_property_data(self, property_id, data_type):
        if self.DEBUG:
            print("Getting data for thing " + str(property_id) + " of type " + str(data_type))
        result = []
        
        if property_id == None or data_type == None:
            print("No thing ID or data type provided")
            return result
        
        if not data_type in ("metricsBoolean", "metricsNumber", "metricsOther"):
            print("data_type not of allowed type")
            return "error"
        
        try:
            db = sqlite3.connect(self.log_db_path)
        except Exception as e:
            print("Error opening log database: " + str(e))
            return "Error opening log database: " + str(e)
            
        try:
            cursor = db.cursor()
            cursor.execute("SELECT date, value FROM " + data_type + " WHERE id=?",(property_id,))
            all_rows = cursor.fetchall()
            
            for row in all_rows:
                #print('date: {0}, value: {1}'.format(row[0],row[1]))
                result.append( {'date':row[0],'value':row[1]} )
            
            db.close()
            return result
    
        except Exception as e:
            print("Get property data: error reading data: " + str(e))
            try:
                db.close()
            except:
                pass
            return "get_property_data: error reading data: " + str(e)
        
        return "ok"
        
        
        
        
    # CHANGE VALUE OF A SINGLE POINT
    def point_change_value(self, action, data_type, property_id, new_value, old_date, new_date):
        print("Asked to change/create data point for property " + str(property_id) + " of type " + str(data_type) + " in table " + str(action) + " to " + str(new_value))
        result = "error"
        
        if property_id == None or action == None:
            print("No action set or property ID provided")
            return "error"
        
        if not data_type in ("metricsBoolean", "metricsNumber", "metricsOther"):
            print("data_type not of allowed type")
            return "error"
        
        if data_type == "metricsBoolean":
            if float(new_value) >= 1:
                new_value = 1
            else:
                new_value = 0
        elif data_type == "metricsNumber":
            try:
                new_value = int(new_value)
            except:
                new_value = float(new_value)
                
        try:
            new_date = int(new_date)
            old_date = int(old_date)
            property_id = int(property_id)
        except:
            print("Error: the date and/or property strings could not be turned into an int")
            return "error"
        
        if self.DEBUG:
            print("action: " + str(action))
            print("At old date " + str(old_date))
            print("and new date " + str(new_date))
            print("changing value to " + str(new_value))
            print("for property " + str(property_id))
            print("of type " + str(data_type))
        
        try:
            db = sqlite3.connect(self.log_db_path)
        except Exception as e:
            print("Error opening log file: " + str(e))
            return "Error opening log file: " + str(e)
            
        try:
            cursor = db.cursor()
            
            if action == "change":
                cursor.execute("UPDATE " + data_type + " SET value=?,date=? WHERE date=? AND id=?", (new_value,new_date,old_date,property_id))
                if cursor.rowcount == 1:
                    db.commit()
                    #result = "ok"
                    result = []
                
                else:
                    return "error" #result = "error"
                    
                    
            elif action == "create":
                print("Creating a new data point")
                #INSERT INTO projects(name,begin_date,end_date) VALUES(?,?,?)
                #cursor.execute("INSERT INTO employees VALUES(1, 'John', 700, 'HR', 'Manager', '2017-01-04')"
                command = "INSERT INTO {}(id,date,value) VALUES({},{},{})".format(data_type, property_id, new_date, new_value)
                print("COMMAND = " + str(command))
                cursor.execute(command)
                #cursor.execute("INSERT INTO " + data_type + " VALUES ?,?,?", (property_id, new_date, new_value,))
                db.commit()
                
                # update cursor position?
                cursor.close()
                cursor = db.cursor()
                result = []

            # If all went well, get all the data points.
            cursor.execute("SELECT date, value FROM " + data_type + " WHERE id=?", (property_id,))
            all_rows = cursor.fetchall()
            #if self.DEBUG:
    
            for row in all_rows:
                #print('date: {0}, value: {1}'.format(row[0],row[1]))
                result.append( {'date':row[0],'value':row[1]} )
                
            db.close()
            return result
    
        except Exception as e:
            print("Error changing point data: " + str(e))
            try:
                db.close()
            except:
                pass
            return "Error changing point data: " + str(e)
        



        
    # DELETE A SINGLE POINT
    
    def point_delete(self,property_id,data_type,start_date,end_date):

        result = "error"
        
        if property_id == None:
            print("No property ID provided")
            return result
        
        if not data_type in ("metricsBoolean", "metricsNumber", "metricsOther"):
            print("data_type not of allowed type")
            return "error"
        
        if self.DEBUG:
            print("Delete from " + str(start_date))
            print("to " + str(end_date))
            print("for ID " + str(property_id))
            print("of data_type " + str(data_type))
        
        try:
            db = sqlite3.connect(self.log_db_path)
        except Exception as e:
            print("Error opening log file: " + str(e))
            return "Error opening log file: " + str(e)
            
        try:
            cursor = db.cursor()
            
            cursor.execute("DELETE FROM " + data_type + " WHERE id=? AND date>=? AND date<=?", (property_id,start_date,end_date,))
            print("cursor.rowcount after deletion = " + str(cursor.rowcount))
            if cursor.rowcount > 0:
                db.commit()
                result = []
                #cursor.close()
                #cursor = db.cursor()
                #Get all the data points.
                cursor.execute("SELECT date, value FROM " + data_type + " WHERE id=?", (property_id,))
                all_rows = cursor.fetchall()
            
                for row in all_rows:
                    print('date: {0}, value: {1}'.format(row[0],row[1]))
                    result.append( {'date':row[0],'value':row[1]} )
                
            else:
                result = "error"
            
            print(str(result))
            db.close()
            return result
    
        except Exception as e:
            print("Error deleting a point: " + str(e))
            try:
                db.close()
            except:
                pass
            return "Error deleting a point: " + str(e)
        





    def internal_logs(self,action,filename):
        print("in internal logs method. Filename: " + str(filename))

        result = []
        
        try:
            # First we delete what needs to be deleted.
            if action == "delete":
                for fname in os.listdir(self.log_dir_path):
                    if fname.startswith("run-app.log") and fname != "run-app.log":
                        if filename == "all":
                            try:
                                os.remove(os.path.join(self.log_dir_path, fname))
                                if self.DEBUG:
                                    print("File deleted")
                            except Exception as ex:
                                if self.DEBUG:
                                    print("Could not delete file: " + str(ex))
                        elif str(filename) == str(fname):
                            print("WILL DELETE A SINGLE FILE: " + str(filename))
                            try:
                                os.remove(os.path.join(self.log_dir_path, fname))
                                if self.DEBUG:
                                    print("File deleted")
                            except Exception as ex:
                                if self.DEBUG:
                                    print("Could not delete file: " + str(ex))
        
            # Secondly, we send a list of (remaining) existing files.
            for fname in os.listdir(self.log_dir_path):
                if fname.startswith("run-app.log") and fname != "run-app.log":
                    result.append(fname)
                        
                        
        except Exception as ex:
            print("Error in log handler: " + str(ex))

        return result


    def unload(self):
        if self.DEBUG:
            print("Shutting down")

