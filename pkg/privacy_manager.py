"""Privacy Manager API handler."""


import os
import re
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import json
import ppa6
import time
#from time import sleep
#from datetime import datetime, timedelta
import pygal
from pygal.style import Style
import sqlite3
import requests
import threading
#import datetime
from datetime import datetime 
#from datetime import date
import functools
import subprocess
#import matplotlib.pyplot as plt

try:
    from PIL import Image
except:
    print("Error: could not load Pillow library. Printing will not be possible.")

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
        
        self.doing_bluetooth_scan = False;
        self.printer = None
        self.do_not_delete_after_printing = False
        
        
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
            self.persistence_file_path = os.path.join(self.user_profile['dataDir'], self.addon_name, 'persistence.json')
            self.chart_png_file_path = os.path.join(self.user_profile['dataDir'], self.addon_name, 'chart.png')
            
            
        except Exception as e:
            print("Failed to further init UX extension API handler: " + str(e))
            
        # Respond to gateway version
        try:
            if self.DEBUG:
                print(self.gateway_version)
        except:
            print("self.gateway_version did not exist")
        
        
        self.persistent_data = {'printer_mac':'', 'printer_name':''}
        
        # Get persistent data
        try:
            with open(self.persistence_file_path) as f:
                self.persistent_data = json.load(f)
                
                if self.DEBUG:
                    print("Persistence data was loaded succesfully.")
                    
                if 'printer_mac' not in self.persistent_data:
                    if self.DEBUG:
                        print("printer_mac was not in persistent data, adding it now.")
                    self.persistent_data['printer_mac'] = ''
                    self.persistent_data['printer_name'] = ''
                    self.save_persistent_data()

        except:
            print("Could not load persistent data (if you just installed the add-on then this is normal)")
            self.save_persistent_data()
        
        self.get_logs_list()
        
        self.connect_to_printer()

        self.running = True
        
        try:
            if self.DEBUG:
                print("Starting the privacy manager clock thread")
            t = threading.Thread(target=self.clock)
            t.daemon = True
            t.start()
        except Exception as ex:
            print("Error starting the clock thread: " + str(ex))
        

        print("Privacy manager init complete")
        
        
        #while(self.running):
        #    time.sleep(1)
        

    def clock(self):
        """ Runs continuously, used by the printer """
        if self.DEBUG:
            print("clock thread init")
        time.sleep(5)
        #last_run = 0
        while self.running:
            #last_run = time.time()
            try:
                if 'printer_interval' in self.persistent_data:
                    my_date = datetime.now()
                    #print("Current hour ", my_date.hour)
                    #print("Current minute ", my_date.minute)
                    if self.persistent_data['printer_interval'] == 'hourly':
                        if my_date.minute == 0:
                            if self.DEBUG:
                                print("HOURLY IS NOW")
                            print_result = self.print_now()
                            if print_result['state'] == 'error':
                                self.print_now()
                            time.sleep(60 * 50) # sleep for 50 minutes
                        
                    elif self.persistent_data['printer_interval'] == 'daily':
                        if my_date.hour == 0 and my_date.minute == 0:
                            if self.DEBUG:
                                print("DAILY IS NOW")
                            print_result = self.print_now()
                            if print_result['state'] == 'error':
                                self.print_now()
                            time.sleep(60 * 50)
                        
                    elif self.persistent_data['printer_interval'] == 'weekly':
                        if datetime.today().weekday() == 0 and my_date.hour == 0 and my_date.minute == 0:
                            if self.DEBUG:
                                print("WEEKLY IS NOW")
                            print_result = self.print_now()
                            if print_result['state'] == 'error':
                                self.print_now()
                            time.sleep(60 * 50)
            
            except Excaption as ex:
                print("error in clock thread: " + str(ex))
            
            #print("clock zzz")
            time.sleep(30)


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
            
        if 'Do not delete after printing' in config:
            self.do_not_delete_after_printing = bool(config['Do not delete after printing'])
            if self.DEBUG:
                print("-Do not delete after printing preference was in config: " + str(self.do_not_delete_after_printing))
            
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
                print("warning, Privacy Manager API received a GET request")
                return APIResponse(status=404)
            
            if request.path == '/ajax' or request.path == '/get_property_data' or request.path == '/point_change_value' or request.path == '/point_delete' or request.path == '/internal_logs' or request.path == '/init' or request.path == '/sculptor_init' or request.path == '/printer_init' or request.path == '/printer_scan' or request.path == '/printer_set' or request.path == '/print_now' or request.path == '/print_test':

                try:
                    
                    if request.path == '/ajax':
                        
                        state = "ok"
                        
                        try:
                            action = str(request.body['action']) 
                        except:
                            print("No specific action provided.")
                        
                        
                        if action == 'quick_delete':
                            print("in quick delete")
                            duration = str(request.body['duration']) 
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : state}),
                            )
                        
                        
                    
                    
                    
                    
                    if request.path == '/init' or request.path == '/sculptor_init' or request.path == '/printer_init':
                        print("in /init or /sculptor_init")
                        # Get the list of properties that are being logged
                        try:
                            logs_list = self.get_logs_list()
                            print(str(logs_list))
                            if isinstance(logs_list, str):
                                state = 'error'
                            else:
                                state = 'ok'
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state': state, 'logs': logs_list, 'scanning': self.doing_bluetooth_scan, 'printer_mac': self.persistent_data['printer_mac'],'printer_name':self.persistent_data['printer_name'], 'persistent': self.persistent_data}),
                            )
                        except Exception as ex:
                            print("Error handling init request: " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps({"state":"error","message":"Error while getting initialisation data: " + str(ex)}),
                            )
                            
                    
                    
                    
                    #elif request.path == '/printer_init':
                    #    return APIResponse(
                    #      status=200,
                    #      content_type='application/json',
                    #      content=json.dumps({'state' : 'ok', 'scanning': self.doing_bluetooth_scan, 'printer_mac': self.persistent_data['printer_mac'],'printer_name':self.persistent_data['printer_name']}),
                    #    )
                    
                            
                            
                    elif request.path == '/printer_scan':
                        try:
                            if self.doing_bluetooth_scan == False:
                                if self.DEBUG:
                                    print("starting bluetooth HCI scan")
                                self.doing_bluetooth_scan = True
                                self.scan_bluetooth()
                                
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : 'ok', 'scanning': self.doing_bluetooth_scan, 'persistent': self.persistent_data}),
                            )
                        except Exception as ex:
                            print("Error handling /printer_scan: " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps({'state': 'error', 'message':'Error while performing bluetooth printer scan: ' + str(ex)}),
                            )
                            
                    
                    
                    elif request.path == '/printer_set':
                        
                        try:
                            
                            print(str(request.body))
                            
                            if 'printer_log' in request.body and 'printer_log_name' in request.body and 'printer_interval' in request.body and 'printer_rotation' in request.body:
                                print("new persistance data received")
                                self.persistent_data['printer_log'] = str(request.body['printer_log']) 
                                self.persistent_data['printer_log_name'] = str(request.body['printer_log_name'])
                                self.persistent_data['printer_interval'] = str(request.body['printer_interval'])
                                self.persistent_data['printer_rotation'] = int(request.body['printer_rotation'])
                            
                            
                                self.save_persistent_data()
                                return APIResponse(
                                  status=200,
                                  content_type='application/json',
                                  content=json.dumps({'state' : 'ok', 'scanning': self.doing_bluetooth_scan, 'persistent': self.persistent_data}),
                                )
                            else:
                                print("new persistance data received, but missing parameters")
                                return APIResponse(
                                  status=500,
                                  content_type='application/json',
                                  content=json.dumps({'state': 'error', 'message':'Missing parameters, very strange'}),
                                )
                            
                        except Exception as ex:
                            print("Error in /printer_set: " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps({'state': 'error', 'message':'Error while setting which log to print: ' + str(ex)}),
                            )
                    
                    
                    elif request.path == '/print_now':
                        
                        try:
                            print("REQUEST TO PRINT NOW")
                            print_result = self.print_now()
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : 'ok', 'print_result': print_result, 'scanning': self.doing_bluetooth_scan, 'printer_mac': self.persistent_data['printer_mac'], 'printer_name':self.persistent_data['printer_name'], 'persistent': self.persistent_data}),
                            )
                        except Exception as ex:
                            print("Error in /print_now: " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps({'state': 'error', 'message':'Error while setting which log to print: ' + str(ex)}),
                            )
                    
                    
                    elif request.path == '/print_test':
                        
                        try:
                            print("REQUEST TO TEST PRINTER")
                            print_result = self.print_test()
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : 'ok', 'print_result': print_result, 'scanning': self.doing_bluetooth_scan, 'persistent': self.persistent_data}),
                            )
                        except Exception as ex:
                            print("Error in /print_now: " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps({'state': 'error', 'message':'Error while doing test print: ' + str(ex)}),
                            )
                    
                    
                    
                    
                    elif request.path == '/get_property_data':
                        try:
                            print("request.body['property_id'] = " + str(request.body['property_id']))
                            if int(request.body['property_id']) in self.data_types_lookup_table:
                                target_data_type = self.data_types_lookup_table[int(request.body['property_id'])]
                                print("target data type from internal lookup table: " + str(target_data_type))
                                data = self.get_property_data( str(request.body['property_id']), str(target_data_type) )
                                if isinstance(data, str):
                                    state = 'error'
                                else:
                                    state = 'ok'
                            
                                return APIResponse(
                                  status=200,
                                  content_type='application/json',
                                  content=json.dumps({'state' : state, 'data' : data}),
                                )
                            else:
                                print("Warning: /get_property_data log id not in lookup table: " + str(self.data_types_lookup_table))
                                return APIResponse(
                                  status=200,
                                  content_type='application/json',
                                  content=json.dumps({'state' : 'ok', 'data' : []}),
                                )
                            
                                    
                            
                        except Exception as ex:
                            print("Error getting log data for log id: " + str(ex))
                            print("Perhaps it wasn't in the lookup table?: " + str(self.data_types_lookup_table))
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
                      content=json.dumps({'state':"Error"}),
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
    def get_logs_list(self):
        if self.DEBUG:
            print("Getting the logs list and updating lookup table")
        
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
                #print("current_title (log id) = " + str(current_title))
                try:
                    cursor.execute("SELECT value FROM metricsNumber WHERE id=?", (row[0],))
                    data_check = cursor.fetchall()
                    #print("metricsNumber data_check = " + str(data_check))
                    
                    if len(data_check) > 0:
                        data_type = "metricsNumber"
                        #print("row[0] = " + str(row[0]))
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
                                print("Datatype also wasn't boolean either. Must be other? Or there currently just isn't any data for this log")
                                # TODO here support for "other" can be added later, if necessary
                        except Exception as ex:
                            print("Error querying if boolean data exists for this item: " + str(ex))

                except Exception as ex:
                    print("Error getting test data to determine data type: " + str(ex))
                    
                #print("data_type = " + str(data_type))
                result.append( {'id':row[0],'name':row[1], 'data_type':data_type} )
                
            db.close()
            print("logs list: " + str(result))
            
            print("self.data_types_lookup_table = " + str(self.data_types_lookup_table))
            return result
    
        except Exception as e:
            print("Init: Error reading data: " + str(e))
            try:
                db.close()
            except:
                pass
            return "Init: general error reading data: " + str(e)



    # GET ALL DATA FOR A SINGLE LOG
    def get_property_data(self, property_id, data_type):
        if self.DEBUG:
            print("Getting data for thing " + str(property_id) + " of type " + str(data_type))
        result = []
        
        if property_id == None or data_type == None:
            print("No thing ID or data type provided")
            return result
        
        if not data_type in ("metricsBoolean", "metricsNumber", "metricsOther"):
            print("data_type not of allowed type")
            return result
        
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
        
        return result
        
        
        
        
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
        



        
    # DELETE POINT(S)
    # NOTE: turn timestamp into milliseconds version (as javascript does)
    
    def point_delete(self,property_id,data_type,start_date,end_date):

        result = []
        
        if property_id == None:
            print("No property ID provided")
            return result
        
        if not data_type in ("metricsBoolean", "metricsNumber", "metricsOther"):
            print("data_type not of allowed type")
            return result
        
        if self.DEBUG:
            print("Delete from " + str(start_date))
            print("to " + str(end_date))
            print("for ID " + str(property_id))
            print("of data_type " + str(data_type))
        
        try:
            db = sqlite3.connect(self.log_db_path)
        except Exception as e:
            print("Error opening log file: " + str(e))
            return []
            
        try:
            cursor = db.cursor()
            
            cursor.execute("DELETE FROM " + data_type + " WHERE id=? AND date>=? AND date<=?", (property_id,start_date,end_date,))
            if self.DEBUG:
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
                    if self.DEBUG:
                        print('date: {0}, value: {1}'.format(row[0],row[1]))
                    result.append( {'date':row[0],'value':row[1]} )
                
            else:
                result = []
            
            #if self.DEBUG:
            #    print("log data after point_delete: " + str(result))
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
        if self.DEBUG:
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
        self.running = False
        if self.printer != None:
            self.printer.disconnect()



    def scan_bluetooth(self):
        """ Checks what bluetooth devices are available"""
        if self.DEBUG:
            print("Starting Bluetooth printer scan")
        
        result = False
        try:
            command = "sudo hcitool scan"
            
            for line in self.run_command_with_lines(command):
                line = line.lower().strip()
                if self.DEBUG:
                    print(str(line))
                
                if 'peripage' in line:
                    result = True
                    if self.DEBUG:
                        print("Peripage printer spotted in Bluetooth scan!")
                    mac_address = extract_mac(line)
                    if self.DEBUG:
                        print("printer mac: " + str(mac_address))
                    
                    self.persistent_data['printer_mac'] = mac_address
                    self.persistent_data['printer_name'] = 'PeriPage printer'
                    try:
                        potential_name = line.rsplit('\t', 1)[1]
                        #print("potential name: X" + str(potential_name) + "X")
                        if 'peripage' in potential_name:
                            #print("printer name: " + str(potential_name))
                            self.persistent_data['printer_name'] = potential_name
                    except Exception as ex:
                        print("Error extracting printer name: " + str(ex))
                    
                    self.save_persistent_data()
                            
        except Exception as e:
            print("Error during Bluetooth printer scan: " + str(e))
        
        if self.DEBUG:
            print("no longer doing Bluetooth scan")
        
        self.doing_bluetooth_scan = False
        
        return result
        
        
    def print_test(self):
        try:
            if self.DEBUG:
                print("doing printer test")
            self.connect_to_printer()
            
            if self.printer.isConnected():
                if self.DEBUG:
                    print("print_test: printer is connected. Printing Hello World.")
                    self.printer.printBreak(1)
                else:
                    self.printer.writeASCII('Hello World\n')
                    self.printer.printBreak(100)
                return True
            
        except Exception as ex:
            print("testprint error: " + str(ex))
        
        return False
        
        
        
    def print_now(self):
        
        try:
            
            if 'printer_log' in self.persistent_data and 'printer_log_name' in self.persistent_data and self.persistent_data['printer_mac'] != '': # and 'printer_interval' in self.persistent_data:
            
                self.get_logs_list()
                
                print_time = int(time.time()) # used to remember up until what moment data should be deleted later on
                if self.DEBUG:
                    print("print time: " + str(print_time))
                    print("log ID: " + str(self.persistent_data['printer_log']) + " = " + str(self.persistent_data['printer_log_name']))
                    print("lookup table: " + str(self.data_types_lookup_table))
                
                try:
                    log_data_type = self.data_types_lookup_table[ int(self.persistent_data['printer_log']) ]
                except Exception as ex:
                    print("could not lookup log data type. Maybe no data?")
                
                if self.DEBUG:
                    print("Log data type: " + str(log_data_type))
                
                
                log_data = self.get_property_data(self.persistent_data['printer_log'], log_data_type)
                if self.DEBUG:
                    print(str(log_data))
                    print("log_data type: " + str(type(log_data)))
                    
                if isinstance(log_data, list): #dict
                    log_data_length = len(log_data)
                    if self.DEBUG:
                        print("log length: " + str(log_data_length))
                    
                    if log_data_length > 1:
                        
                        # Define Data

                        #x= [1, 2, 3, 4, 5]
                        #y= [2.5, 6.3, 12, 14, 2]

                        # Plot 

                        #plt.plot(x,y,color='r')
                        #plt.plot()
                        
                        """
                        secs = [x['date'] for x in log_data]
                        vals = [x['value'] for x in log_data]
                        print("seconds:")
                        print(str(secs))
                        
                        print(" ")
                        print("values:")
                        print(str(vals))
                        """
                        
                        #plt.plot(secs, vals)
                        
                        
                        #plt.plot(log_data.date, log_data.value)

                        # Save image as png

                        #plt.savefig(self.chart_png_file_path)
                        
                        
                        
                        """
                        
                        custom_style = Style(
                          background='transparent',
                          plot_background='transparent',
                          foreground='#53E89B',
                          foreground_strong='#53A0E8',
                          foreground_subtle='#630C0D',
                          opacity='.6',
                          opacity_hover='.9',
                          transition='400ms ease-in',
                          colors=('#E853A0', '#E8537A', '#E95355', '#E87653', '#E89B53'))

                        chart = pygal.StackedLine(fill=True, interpolate='cubic', style=custom_style)
                        chart.add('A', [1, 3,  5, 16, 13, 3,  7])
                        chart.add('B', [5, 2,  3,  2,  5, 7, 17])
                        chart.add('C', [6, 10, 9,  7,  3, 1,  0])
                        chart.add('D', [2,  3, 5,  9, 12, 9,  5])
                        chart.add('E', [7,  4, 2,  1,  2, 10, 0])
                        chart.render()
                        
                        print("ok, demo worked")
                        
                        
                        custom_style = Style(
                          background='transparent',
                          plot_background='transparent',
                          foreground='#53E89B',
                          foreground_strong='#000000',
                          foreground_subtle='#666666',
                          opacity='1',
                          title_font_size='36',
                          label_font_size='16',
                          major_label_font_size='24',
                          value_font_size='24',
                          value_label_font_size='24',
                          colors=('#000000', '#333333', '#666666', '#999999', '#CCCCCC'))
                        
                        
                        custom_style = Style(
                          background='#fff',
                          plot_background='transparent',
                          opacity='1',
                          value_label_font_size='24')
                        
                        #line_chart = pygal.Line(style=custom_style)
                        line_chart = pygal.DateLine()
                        
                        line_chart.title = self.persistent_data['printer_log_name']
                        
                        if self.persistent_data['printer_interval'] == 'none':
                            print("interval is none! Should not continue")
                            return {'state':'error','message':'interval is disabled'}
                        
                        elif self.persistent_data['printer_interval'] == 'hourly':
                            print("HOUR: " + str( time.strftime("%H") ))
                            
                            current_hour = int(time.strftime("%H"))
                            previous_hour = current_hour - 1
                            if current_hour == 0:
                                previous_hour = 23
                                
                            print(str(current_hour))
                            print(str(previous_hour))
                            line_chart.x_labels = [str(previous_hour), ':15', ':30',':45', str(current_hour)] #map(str, range(2002, 2013))
                            
                        elif self.persistent_data['printer_interval'] == 'daily':
                            line_chart.x_labels = map(str, range(0, 24))
                            
                        elif self.persistent_data['printer_interval'] == 'weekly':
                            line_chart.x_labels = ['m','t','w','t','f','s','s']
                        
                        #line_chart.x_labels = [] #map(str, range(2002, 2013))
                        
                        #counter = 0
                        #start = "start"
                        #end = "end"
                        values = []
                        for log_item in log_data:
                            #print(str(log_item))
                            date = log_item['date']
                            value = log_item['value']
                            #print(str(date) + " -> " + str(value))
                            values.append(value)
                            #if counter == 0:
                            #    start = date
                            
                        
                        print("log data parsed into array : " + str(values))
                            
                        line_chart.add('y', values, dots_size=4)
                        print("values added to pygal")
                        #line_chart.add('Chrome',  [None, None, None, None, None, None,    0,  3.9, 10.8, 23.8, 35.3])
                        #line_chart.add('IE',      [85.8, 84.6, 84.7, 74.5,   66, 58.6, 54.7, 44.8, 36.2, 26.6, 20.1])
                        #line_chart.add('Others',  [14.2, 15.4, 15.3,  8.9,    9, 10.4,  8.9,  5.8,  6.7,  6.8,  7.5])
                        line_chart.render()
                        print("linechart render done?!")
                        
                        line_chart.render_to_png(self.chart_png_file_path)
                        """
                        
                        custom_style = Style(
                          background='#fff',
                          #title_font_size='3',
                          major_label_font_size='30',
                          value_label_font_size='30')
                        
                        counter = 0
                        values = []
                        for log_item in log_data:
                            counter += 1
                            
                            #print(str(log_item))
                            date = log_item['date']
                            value = log_item['value']
                            #print(str(date) + " -> " + str(value))
                            #values.append(value)
                            values.append(( round(date/1000), value ))
                            #if counter == 0:
                            #    start = date
                            #if counter == 20:
                            #    print("breaking out of values loop")
                            #    break
                        
                        #some_list = []
                        #some_list.append((a, b))
                        #print("new values: " + str(values))
                        
                        
                        # pygal.graph.time.seconds_to_time

                        

                        if self.DEBUG:
                            print("amount of values to print: " + str(len(values)))
                        
                        dataviz_width = 304
                        if len(values) > 152:
                            dataviz_width = len(values) * 2

                        #dateline = pygal.DateLine(x_label_rotation=45, range=(0, 750))
                        dateline = pygal.DateLine(x_label_rotation=30, style=custom_style, width=dataviz_width, height=200)
                        if self.DEBUG:
                            print("dateLine init done")
                        
                        dateline.title = self.persistent_data['printer_log_name']
                        
                        """
                        if self.persistent_data['printer_interval'] == 'none':
                            print("interval is none! Should not continue")
                            return {'state':'error','message':'interval is disabled'}
                        
                        elif self.persistent_data['printer_interval'] == 'hourly':
                            print("HOUR: " + str( time.strftime("%H") ))
                            
                            current_hour = int(time.strftime("%H"))
                            previous_hour = current_hour - 1
                            if current_hour == 0:
                                previous_hour = 23
                                
                            print(str(current_hour))
                            print(str(previous_hour))
                            dateline.x_labels = [str(previous_hour), ':15', ':30',':45', str(current_hour)] #map(str, range(2002, 2013))
                            
                        elif self.persistent_data['printer_interval'] == 'daily':
                            dateline.x_labels = map(str, range(0, 24))
                            
                        elif self.persistent_data['printer_interval'] == 'weekly':
                            dateline.x_labels = ['m','t','w','t','f','s','s']
                        """
                        
                        
                        """
                        dateline.x_labels = [
                                date(2014, 1, 1),
                                date(2014, 3, 1),
                                date(2014, 5, 1),
                                date(2014, 7, 1),
                                date(2014, 9, 1),
                                date(2014, 11, 1),
                                date(2014, 12, 31)
                        ]
                        """
                        #print("next, adding time pairs")
                        #dateline.add('Time', [
                        #        (1389830399, 400),
                        #        (1402826470, 450),
                        #        (1420029285, 500)])
                        dateline.add('',values) #, dots_size=4)


                        dateline.render_to_png(self.chart_png_file_path)
                        
                        if self.DEBUG:
                            print("DateLine dataviz generated. Attempting to (re)connect to printer")
                        self.connect_to_printer()
                        
                        if self.printer.isConnected():
                            if self.DEBUG:
                                print("print_now: printer is connected!")
                            
                            #print(f'Full: {printer.getDeviceFull()}')
                            
                            self.printer.setConcentration(2)
                            
                            img = None
                            
                            try:
                                img = Image.open(self.chart_png_file_path).convert('RGBA')
                                if 'printer_rotation' in self.persistent_data:
                                    if self.DEBUG:
                                        print("rotation preference was present: " + str(self.persistent_data['printer_rotation']))
                                    if int(self.persistent_data['printer_rotation']) != 0:
                                        if self.DEBUG:
                                            print("rotating image")
                                        img2 = img.rotate(int(self.persistent_data['printer_rotation']), expand=True)
                                    else:
                                        img2 = img
                                else:
                                    img2 = img
                            except Exception as ex:
                                print('Error rotating image: ' + str(ex))
    
        
                            if self.DEBUG:
                                print("Printing log image now")
                            self.printer.printImage(img2, resample=Image.ANTIALIAS)
                            
                            if self.DEBUG:
                                print("printing break")
                            self.printer.printBreak(100)
                            
                            if self.do_not_delete_after_printing == False: # and self.DEBUG == False:
                                print("about to delete data, since print was successful (if the paper hasn't run out...)")                                
                                self.point_delete(self.persistent_data['printer_log'],log_data_type,0, print_time * 1000 ) # deletes all data in the log
                            
                            return {'state':'ok','message':'Log was printed'}
                            
                        else:
                            print("print_now: error, not connected to printer")
                            return {'state':'error','message':'Could not connect to printer'}
                        
                    elif log_data_length == 1:
                        print("only one data point in this period")
                        
                        return {'state':'ok','message':'Log only had one datapoint. It was printed as text.'}
                        
                    elif log_data_length == 0:
                        print("no data point in this period")
                        
                        return {'state':'ok','message':'Log did not contain any data points'}
                
                else:
                    print("Error: log data could not be loaded")
                    return {'state':'error','message':'Log data could not be loaded.'}
            else:
                print("missing parameters")
                return {'state':'error','message':'Missing parameters, could not print. Check and save your settings.'}
            
            

            
            
            #line_chart.render_to_file('/home/pi/linechart.svg')
            
            
            #print("creating print_me var")
            #print_me = line_chart.render()
            #print("type: " + str(type(print_me)))
            
            
        
            #printer.writeASCII('Hello World?\n')
            #printer.printBreak(100)




            # Set print concentration
            
            """
            # Print image & break
            try:
                printer.printImage(print_me)
            except Exception as ex:
                print("printing print_me bytes failed: " + str(ex))
            
            print("printing break")
            printer.printBreak(10)
            
            img = None
        
            
            try:
                img = Image.open('/home/pi/linechart.png')
                img.rotate(180)
            except:
                print(f'Failed to open image /home/pi/linechart.png')
        
            
        
            printer.printImage(img, resample=Image.ANTIALIAS)
            
            print("PRINT NOW SUCCESSFULLY REACHED END")
            
            
            bar_chart = pygal.Bar()
            bar_chart.title = 'Browser usage evolution (in %)'
            bar_chart.x_labels = map(str, range(2002, 2013))
            bar_chart.add('Firefox', [None, None, 0, 16.6,   25,   31, 36.4, 45.5, 46.3, 42.8, 37.1])
            bar_chart.add('Chrome',  [None, None, None, None, None, None,    0,  3.9, 10.8, 23.8, 35.3])
            bar_chart.add('IE',      [85.8, 84.6, 84.7, 74.5,   66, 58.6, 54.7, 44.8, 36.2, 26.6, 20.1])
            bar_chart.add('Others',  [14.2, 15.4, 15.3,  8.9,    9, 10.4,  8.9,  5.8,  6.7,  6.8,  7.5])
            bar_chart.render()
            
            bar_chart.render_to_png('/home/pi/barchart.png')
            
            try:
                img = Image.open('/home/pi/barchart.png')
                img.rotate(180)
            except:
                print(f'Failed to open image /home/pi/linechart.png')
        
            
            
            #printer.printImage(img, resample=Image.ANTIALIAS)
            
            
            printer.printBreak(10)
            
            print("PRINTED BAR CHART")
            """
            
            
        except Exception as e:
            print("ERROR in print_now: " + str(e))
            return {'state':'error','message':'General error in print_now'}


    def connect_to_printer(self):
        print("in connect_to_printer")
        try:
            if self.printer == None and self.persistent_data['printer_mac'] != '':
                print("creating printer object with mac: " + str(self.persistent_data['printer_mac']))
                self.printer = ppa6.Printer(self.persistent_data['printer_mac'], ppa6.PrinterType.A6p)
                
            if self.printer != None:
                if self.DEBUG:
                    print("printer object exists")
                if self.printer.isConnected() == False:
                    if self.DEBUG:
                        print("Printer is not connected. Will attempt to connect.")
                    try:
                        self.printer.connect()
                        self.printer.reset()
                    except:
                        if self.DEBUG:
                            print("printer.connect didn't work, trying reconnect instead")
                        try:
                            self.printer.reconnect()
                            self.printer.reset()
                        except:
                            if self.DEBUG:
                                print("printer.reconnect also didn't work")
                        
                if self.printer.isConnected():
                    if self.DEBUG:
                        print(f'Name: {self.printer.getDeviceName()}')
                        print(f'S/N: {self.printer.getDeviceSerialNumber()}')
                        print(f'F/W: {self.printer.getDeviceFirmware()}')
                        print(f'Battery: {self.printer.getDeviceBattery()}%')
                        print(f'H/W: {self.printer.getDeviceHardware()}')
                        print(f'MAC: {self.printer.getDeviceMAC()}')
                else:
                    print("ERROR, was unable to (re)connect to the printer")
                    
            else:
                if self.DEBUG:
                    print("printer has not been set up yet.")
                        
        except Exception as ex:
            print("error setting up printer: " + str(ex))



    def save_persistent_data(self):
        if self.DEBUG:
            print("Saving to persistence data store at path: " + str(self.persistence_file_path))
            
        try:
            if not os.path.isfile(self.persistence_file_path):
                open(self.persistence_file_path, 'a').close()
                if self.DEBUG:
                    print("Created an empty persistence file")
            else:
                if self.DEBUG:
                    print("Persistence file existed. Will try to save to it.")

            with open(self.persistence_file_path) as f:
                #if self.DEBUG:
                #    print("saving persistent data: " + str(self.persistent_data))
                json.dump( self.persistent_data, open( self.persistence_file_path, 'w+' ) )
                if self.DEBUG:
                    print("Data stored")
                return True

        except Exception as ex:
            print("Error: could not store data in persistent store: " + str(ex) )
            print(str(self.persistent_data))
            return False



    def run_command_with_lines(self,command):
        try:
            p = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True)
            # Read stdout from subprocess until the buffer is empty !
            for bline in iter(p.stdout.readline, b''):
                line = bline.decode('utf-8') #decodedLine = lines.decode('ISO-8859-1')
                line = line.rstrip()
                if line: # Don't print blank lines
                    yield line
                
            # This ensures the process has completed, AND sets the 'returncode' attr
            while p.poll() is None:                                                                                                                                        
                time.sleep(.1) #Don't waste CPU-cycles
            # Empty STDERR buffer
            err = p.stderr.read()
            if p.returncode == 0:
                yield("Command success")
                return True
            else:
                # The run_command() function is responsible for logging STDERR 
                if len(err) > 1:
                    yield("Command failed with error: " + str(err.decode('utf-8')))
                    return False
                yield("Command failed")
                return False
                #return False
        except Exception as ex:
            print("Error running shell command: " + str(ex))
    

def extract_mac(line):
    #p = re.compile(r'(?:[0-9a-fA-F]:?){12}')
    p = re.compile(r'((([a-zA-z0-9]{2}[-:]){5}([a-zA-z0-9]{2}))|(([a-zA-z0-9]{2}:){5}([a-zA-z0-9]{2})))')
    # from https://stackoverflow.com/questions/4260467/what-is-a-regular-expression-for-a-mac-address
    return re.findall(p, line)[0][0]

def valid_mac(mac):
    return mac.count(':') == 5 and \
        all(0 <= int(num, 16) < 256 for num in mac.rstrip().split(':')) and \
        not all(int(num, 16) == 255 for num in mac.rstrip().split(':'))
