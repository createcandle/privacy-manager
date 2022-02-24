"""Privacy Manager API handler."""


import os
import re
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import json
import ppa6
#import time
import time as time_module
#from time import sleep
#from datetime import datetime, timedelta
import pygal
from pygal.style import Style
import sqlite3
import requests
import threading
#import datetime
from datetime import time,date,datetime,timedelta,timezone
#from datetime import date
import functools
import subprocess
#import matplotlib.pyplot as plt

try:
    from PIL import Image
except:
    print("Error: could not load Pillow library. Printing will not be possible.")

try:
    from gateway_addon import Database, APIHandler, APIResponse
    #print("succesfully loaded APIHandler and APIResponse from gateway_addon")
except:
    print("Could not load vital libraries to interact with the controller, exiting.")
    sys.exit(1)
    
from .privacy_manager_adapter import *

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
        
        self.adapter = None    
        
        self.things = [] # Holds all the things, updated via the API. Used to display a nicer thing name instead of the technical internal ID.
        self.data_types_lookup_table = {}
        self.duration_lookup_table = {'1':'1 minute',
                                    '10':'10 minutes',
                                    '20':'20 minutes',
                                    '60':'1 hour',
                                    '120':'2 hours',
                                    '240':'4 hours',
                                    '480':'8 hours',
                                }
                                
        # printer
        self.doing_bluetooth_scan = False
        self.printer = None
        self.busy_connecting_to_printer = False
        self.printer_connected = False
        self.printer_connection_counter = 0
        self.printer_contrast = 1
        self.do_not_delete_after_printing = False # only used during development
        self.should_print_log_name = False
        self.date_string_to_print = ""
        self.power_timeout_set = False
        self.last_printer_check_time = 0
        self.printer_disconnected_counter = 0
        self.printer_disconnected_retry_delay = 30 # can be as low as 30 seconds initially, then slowly grows to about 10 minutes between reconnect attempts
        
        
        
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
            
            self.external_picture_drop_dir = os.path.join(self.user_profile['dataDir'], self.addon_name, 'printme')
            
            
        except Exception as e:
            print("Failed to further init UX extension API handler: " + str(e))
            
        # Respond to gateway version
        try:
            if self.DEBUG:
                print(self.gateway_version)
        except:
            print("self.gateway_version did not exist")
        
        
        self.persistent_data = {'printer_mac':'', 'printer_name':'','internal_logs_auto_delete':True}
        
        should_save_persistent_data = False
        # Get persistent data
        try:
            with open(self.persistence_file_path) as f:
                self.persistent_data = json.load(f)
                
                if self.DEBUG:
                    print("Persistence data was loaded succesfully.")
                    
                

        except:
            print("Could not load persistent data (if you just installed the add-on then this is normal)")
            self.persistent_data = {'printer_mac':'', 'printer_name':'','internal_logs_auto_delete':True}
            should_save_persistent_data = True
        
        if 'printer_mac' not in self.persistent_data:
            if self.DEBUG:
                print("printer_mac was not in persistent data, adding it now.")
            self.persistent_data['printer_mac'] = ''
            self.persistent_data['printer_name'] = ''
            should_save_persistent_data = True

        if 'internal_logs_auto_delete' not in self.persistent_data:
            self.persistent_data['internal_logs_auto_delete'] = True
            should_save_persistent_data = True
        
        if 'duration' not in self.persistent_data:
            self.persistent_data['duration'] = 30
            should_save_persistent_data = True
        
        if 'printer_log_name' not in self.persistent_data:
            self.persistent_data['printer_log_name'] = ""
            should_save_persistent_data = True
            
        if 'printer_contrast' not in self.persistent_data:
            self.persistent_data['printer_contrast'] = 'medium'
            should_save_persistent_data = True
        
        if should_save_persistent_data:
            self.save_persistent_data()
        
        self.get_logs_list()
        
        self.connect_to_printer()
        
        if self.printer != None:
            if not os.path.isdir(self.external_picture_drop_dir):
                if self.DEBUG:
                    print("Creating image dropoff directory")
                os.makedirs(self.external_picture_drop_dir)
            
            #os.system('rm ' + str(self.external_picture_drop_dir) + '/*') # maybe a bit too dangerous
        
        
        try:
            self.adapter = PrivacyManagerAdapter(self,verbose=False)
            #self.manager_proxy.add_api_handler(self.extension)
            if self.DEBUG:
                print("ADAPTER created")
        except Exception as ex:
            print("Failed to start ADAPTER. Error: " + str(ex))
        
        self.running = True
        
        try:
            if self.DEBUG:
                print("Starting the privacy manager clock thread")
            t = threading.Thread(target=self.clock)
            t.daemon = True
            t.start()
        except Exception as ex:
            print("Error starting the clock thread: " + str(ex))
        

        if self.DEBUG:
            print("Privacy manager init complete")
        
        
        #while(self.running):
        #    time_module.sleep(1)
        

    def clock(self):
        """ Runs continuously, used by the printer """
        if self.DEBUG:
            print("clock thread init")
        time_module.sleep(5)
        #last_run = 0
        previous_scheduled_print_time = 0
        #previous_printer_battery_check_time = 0
        #self.printer_connection_counter = 0
        
        while self.running:
            #last_run = time_module.time()
            try:
                if 'printer_interval' in self.persistent_data:
                    current_datetime = datetime.now()
                    timestamp = int(round(current_datetime.timestamp()))
                    #print("Current hour ", current_datetime.hour)
                    #print("Current minute ", current_datetime.minute)
                    
                    if timestamp - previous_scheduled_print_time > 120:
                        previous_scheduled_print_time = timestamp
                        
                        if self.persistent_data['printer_interval'] == 'hourly':
                            if current_datetime.minute == 0:
                                if self.DEBUG:
                                    print("HOURLY IS NOW")
                                print_result = self.print_now()
                                #if print_result['state'] == 'error':
                                #    self.print_now()
                                #time_module.sleep(60)
                        
                        if self.persistent_data['printer_interval'] == '3hourly':
                            if current_datetime.minute == 0 and current_datetime.hour % 3 == 0:
                                if self.DEBUG:
                                    print("3HOURLY IS NOW")
                                print_result = self.print_now()
                                #if print_result['state'] == 'error':
                                #    self.print_now()
                                #time_module.sleep(60)
                        
                        if self.persistent_data['printer_interval'] == '6hourly':
                            if current_datetime.minute == 0  and current_datetime.hour % 6 == 0:
                                if self.DEBUG:
                                    print("6HOURLY IS NOW")
                                print_result = self.print_now()
                                #if print_result['state'] == 'error':
                                #    self.print_now()
                                #time_module.sleep(60)
                            
                        if self.persistent_data['printer_interval'] == '12hourly':
                            if current_datetime.minute == 0  and current_datetime.hour % 12 == 0:
                                if self.DEBUG:
                                    print("12HOURLY IS NOW")
                                print_result = self.print_now()
                                #if print_result['state'] == 'error':
                                #    self.print_now()
                                #time_module.sleep(60)
                        
                        elif self.persistent_data['printer_interval'] == 'daily':
                            if current_datetime.hour == 0 and current_datetime.minute == 0:
                                if self.DEBUG:
                                    print("DAILY IS NOW")
                                print_result = self.print_now()
                                #if print_result['state'] == 'error':
                                #    self.print_now()
                                #time_module.sleep(60)
                        
                        elif self.persistent_data['printer_interval'] == 'weekly':
                            if datetime.today().weekday() == 0 and current_datetime.hour == 0 and current_datetime.minute == 0:
                                if self.DEBUG:
                                    print("WEEKLY IS NOW")
                                print_result = self.print_now()
                                #if print_result['state'] == 'error':
                                #    self.print_now()
                                #time_module.sleep(60)
            
            
                        # If internal logs should be auto-deleted, it will be attempted once per hour.
                        if self.persistent_data['internal_logs_auto_delete'] == True and self.DEBUG == False:
                            if current_datetime.minute == 3:
                                if self.DEBUG:
                                    print("Attempting to auto-delete internal logs")
                                
                                delete_internal_logs_outcome = self.internal_logs("delete", "all")
                                if isinstance(delete_internal_logs_outcome, str):
                                    if self.DEBUG:
                                        print("Error while trying to delete internal logs: " + str(delete_internal_logs_outcome))
                                #time_module.sleep(60)
                            
            
            except Exception as ex:
                print("error in clock thread: " + str(ex))
            
            #print("clock zzz")
            time_module.sleep(1)
            
            # Keep bluetooth connection to printer alive
            if not self.busy_connecting_to_printer:
                try:
                    if self.printer != None:
                        if self.printer_connected:
                            self.printer_connection_counter += 1
                            self.printer_disconnected_retry_delay = 30
                            #if timestamp - previous_printer_battery_check_time > 30:
                            if self.printer_connection_counter > 28:
                                if self.DEBUG:
                                    print("requesting battery level from printer to keep it awake")
                                self.printer_connection_counter = 0
                                self.printer_battery_level = self.printer.getDeviceBattery()
                                if self.DEBUG:
                                    print("self.printer_battery_level: " + str(self.printer_battery_level))
                                try:
                                    if 'printer_battery' in self.adapter.thing.properties:
                                        self.adapter.thing.properties['printer_battery'].update(int(self.printer_battery_level))
                                except Exception as ex:
                                    print("error updating battery level on thing: " + str(ex))
                        else:
                            self.printer_disconnected_counter += 1
                            if self.printer_disconnected_counter > self.printer_disconnected_retry_delay:
                                self.printer_disconnected_counter = 0
                                if self.print_test():
                                    if self.DEBUG:
                                        print("Clock: succesfully reconnected to printer")
                                    else:
                                        if self.printer_disconnected_retry_delay < 600:
                                            self.printer_disconnected_retry_delay += 60
                                        if self.DEBUG:
                                            print("Clock: could not reconnect to printer")
                            
                            
                        #if self.DEBUG:
                        #    print(f'Printer battery level: {self.printer_battery_level}%')
                except Exception as ex:
                    if self.DEBUG:
                        print("Error with periodic connnection upkeep to printer: " + str(ex))
                    #self.printer_connected = False

                    
            # print any picture that appears
            try:
                if self.printer != None:
                    if self.persistent_data['printer_mac'] != '':
                        
                        with os.scandir(self.external_picture_drop_dir) as files:
                            for item in files:
                                if item.is_file():
                                    filename = os.path.join(self.external_picture_drop_dir, str(item.name))
                                    if self.DEBUG:
                                        print(" picture(s) spotted in the external drop-off location: " + str(filename))
                                    self.print_image_file(filename)
                                    time_module.sleep(10)
                                    break
                            
                        
            except Exception as ex:
                if self.DEBUG:
                    print("Error with periodic connnection upkeep to printer: " + str(ex))
            


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
            exit()
        
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
            
            if request.path == '/ajax' or request.path == '/get_property_data' or request.path == '/point_change_value' or request.path == '/point_delete' or request.path == '/internal_logs' or request.path == '/init' or request.path == '/sculptor_init' or request.path == '/printer_init' or request.path == '/printer_scan' or request.path == '/printer_set' or request.path == '/print_now' or request.path == '/print_test' or request.path == '/print_image':

                try:
                    if request.path == '/ajax':
    
                        state = "ok"
                        
                        try:
                            action = str(request.body['action']) 
                        except:
                            print("No specific action provided.")
                        
                        
                        if action == 'quick_delete':
                            if self.DEBUG:
                                print("in quick delete")
                            self.persistent_data['duration'] = int(request.body['duration'])
                            self.save_persistent_data()
                            self.quick_delete_filter(self.persistent_data['duration'])
                            
                            # set duration on thing too
                            self.adapter.thing.properties["data_deletion_duration"].update(self.persistent_data['duration'])
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : state}),
                            )
                        
                        
                    
                    
                    
                    
                    if request.path == '/init' or request.path == '/sculptor_init' or request.path == '/printer_init':
                        #print("handling API request to /init or /sculptor_init")
                        # Get the list of properties that are being logged
                        try:
                            logs_list = self.get_logs_list()
                            #print(str(logs_list))
                            if isinstance(logs_list, str):
                                state = 'error'
                            else:
                                state = 'ok'
                                
                            internal_logs_auto_delete = False
                            try:
                                internal_logs_auto_delete = bool(self.persistent_data['internal_logs_auto_delete'])
                            except Exception as ex:
                                print("internal_logs_auto_delete init error: " + str(ex))
                                self.persistent_data['internal_logs_auto_delete'] = False
                                self.save_persistent_data()
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state': state, 'logs': logs_list, 'scanning': self.doing_bluetooth_scan, 'persistent': self.persistent_data, 'printer_connected':self.printer_connected, 'internal_logs_auto_delete': internal_logs_auto_delete, 'debug': self.DEBUG}),
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
                            
                            if self.DEBUG:
                                print(str(request.body))
                            
                            if 'printer_log' in request.body and 'printer_log_name' in request.body and 'printer_interval' in request.body and 'printer_rotation' in request.body:
                                print("new persistance data received")
                                
                                if self.persistent_data['printer_log_name'] != str(request.body['printer_log_name']):
                                    if self.DEBUG:
                                        print("The log name will be printed next time")
                                    self.should_print_log_name = True
                                
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
                            if self.DEBUG:
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
                            if self.DEBUG:
                                print("REQUEST TO TEST PRINTER")
                            printer_connected = self.print_test()
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : 'ok', 'printer_connected': printer_connected, 'scanning': self.doing_bluetooth_scan, 'persistent': self.persistent_data}),
                            )
                        except Exception as ex:
                            print("Error in /print_now: " + str(ex))
                            return APIResponse(
                              status=500,
                              content_type='application/json',
                              content=json.dumps({'state': 'error', 'message':'Error while doing test print: ' + str(ex)}),
                            )
                    
                    
                    elif request.path == '/print_image':
                        try:
                            state = 'ok'
                            if self.DEBUG:
                                print("REQUEST TO PRINT ICON")
                            
                            if 'filename' in request.body:
                                filename = request.body['filename']
                                icon_path =  os.path.join(self.addon_path, 'images', filename)
                                if os.path.isfile(icon_path) and os.path.isdir(self.external_picture_drop_dir):
                                    destination_path =  os.path.join(self.external_picture_drop_dir, filename)
                                    copy_command = 'cp ' + str(icon_path) + ' ' + destination_path
                                    if self.DEBUG:
                                        print("copying icon to drop-off dir. Copy command: " + str(copy_command))
                                    os.system(copy_command)
                                else:
                                    state = 'error'
                            else:
                                state = 'error'
                            
                            return APIResponse(
                              status=200,
                              content_type='application/json',
                              content=json.dumps({'state' : state}),
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
                            if self.DEBUG:
                                print("request.body['property_id'] = " + str(request.body['property_id']))
                            if int(request.body['property_id']) in self.data_types_lookup_table:
                                target_data_type = self.data_types_lookup_table[int(request.body['property_id'])]
                                if self.DEBUG:
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
                            if self.DEBUG:
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
                        if self.DEBUG:
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
                        if self.DEBUG:
                            print("/INTERNAL_LOGS CALLED")
                        try:
                            data = []
                            state = "ok"
                            action = "get"
                            filename = "all"
                            
                            try:
                                action = str(request.body['action']) 
                            except:
                                print("Warning, no specific action provided.")
                                
                            try:
                                filename = str(request.body['filename']) 
                            except:
                                if self.DEBUG:
                                    print("Internal logs API: no specific filename provided")
                                
                            if action == "auto-delete":
                                internal_logs_auto_delete = bool(request.body['internal_logs_auto_delete'])
                                self.persistent_data['internal_logs_auto_delete'] = internal_logs_auto_delete
                                self.save_persistent_data()
                                if internal_logs_auto_delete:
                                    action = "delete" # immediately delete all internal logs
                                
                            # getting list of internal logs, deleting a single internal log, deleting all internal logs

                        
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
                    print("general error handling API request: " + str(ex))
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
    def get_logs_list(self): # for data sculptor
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
            #print(str(all_rows))
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
                        #if self.DEBUG:
                        #    print("Data type for this log is Number")
                            
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
                                if self.DEBUG:
                                    print("Likely spotted an empty log")
                                # TODO here support for "other" can be added later, if necessary
                        except Exception as ex:
                            print("Error querying if boolean data exists for this item: " + str(ex))

                except Exception as ex:
                    print("Error getting test data to determine data type: " + str(ex))
                    
                #print("data_type = " + str(data_type))
                result.append( {'id':row[0],'name':row[1], 'data_type':data_type} )
                
            db.close()
            if self.DEBUG:
                print("logs list: " + str(result))
                print("self.data_types_lookup_table = " + str(self.data_types_lookup_table))
            return result
    
        except Exception as e:
            if self.DEBUG:
                print("Init: Error reading data: " + str(e))
            try:
                db.close()
            except:
                pass
            return "Init: general error reading data: " + str(e)



    # GET ALL DATA FOR A SINGLE LOG
    def get_property_data(self, property_id, data_type):
        if self.DEBUG:
            print("Getting data for single log: " + str(property_id) + ", of type: " + str(data_type))
        result = []
        
        if property_id == None or data_type == None:
            if self.DEBUG:
                print("No thing ID or data type provided")
            return result
        
        if not data_type in ("metricsBoolean", "metricsNumber", "metricsOther"):
            if self.DEBUG:
                print("data_type not of allowed type")
            return result
        
        try:
            db = sqlite3.connect(self.log_db_path)
        except Exception as e:
            if self.DEBUG:
                print("Error opening log database: " + str(e))
            return "Error opening log database: " + str(e)
            
        if self.DEBUG:
            print("sqlite3 db connected")
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
            if self.DEBUG:
                print("Get property data: error reading data: " + str(e))
            try:
                db.close()
            except:
                pass
            return "get_property_data: error reading data: " + str(e)
        
        return result
        
        
        
        
    # CHANGE VALUE OF A SINGLE POINT
    def point_change_value(self, action, data_type, property_id, new_value, old_date, new_date):
        #if self.DEBUG:
        #    print("Asked to change/create data point for property " + str(property_id) + " of type " + str(data_type) + " in table " + str(action) + " to " + str(new_value))
        result = "error"
        
        if property_id == None or action == None:
            if self.DEBUG:
                print("No action set or property ID provided")
            return "error"
        
        if not data_type in ("metricsBoolean", "metricsNumber", "metricsOther"):
            if self.DEBUG:
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
            #if self.DEBUG:
            #    print("Error: the date and/or property strings could not be turned into an int")
            return "error"
        
        #if self.DEBUG:
        #    print("action: " + str(action))
        #    print("At old date " + str(old_date))
        #    print("and new date " + str(new_date))
        #    print("changing value to " + str(new_value))
        #    print("for property " + str(property_id))
        #    print("of type " + str(data_type))
        
        try:
            db = sqlite3.connect(self.log_db_path)
        except Exception as e:
            if self.DEBUG:
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
                #if self.DEBUG:
                #    print("Creating a new data point")
                #INSERT INTO projects(name,begin_date,end_date) VALUES(?,?,?)
                #cursor.execute("INSERT INTO employees VALUES(1, 'John', 700, 'HR', 'Manager', '2017-01-04')"
                command = "INSERT INTO {}(id,date,value) VALUES({},{},{})".format(data_type, property_id, new_date, new_value)
                #if self.DEBUG:
                #    print("COMMAND = " + str(command))
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
            #if self.DEBUG:
            #    print("Error changing point data: " + str(e))
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
            if self.DEBUG:
                print("No property ID provided")
            return result
        
        if not data_type in ("metricsBoolean", "metricsNumber", "metricsOther"):
            if self.DEBUG:
                print("data_type not of allowed type")
            return result
        
        #if self.DEBUG:
        #    print("Delete from " + str(start_date))
        #    print("to " + str(end_date))
        #    print("for ID " + str(property_id))
        #    print("of data_type " + str(data_type))
        
        try:
            db = sqlite3.connect(self.log_db_path)
        except Exception as e:
            if self.DEBUG:
                print("Error opening log file: " + str(e))
            return []
            
        try:
            cursor = db.cursor()
            
            cursor.execute("DELETE FROM " + data_type + " WHERE id=? AND date>=? AND date<=?", (property_id,start_date,end_date,))
            #if self.DEBUG:
            #    print("cursor.rowcount after deletion = " + str(cursor.rowcount))
            
            if cursor.rowcount > 0:
                db.commit()
                result = []
                #cursor.close()
                #cursor = db.cursor()
                #Get all the data points.
                cursor.execute("SELECT date, value FROM " + data_type + " WHERE id=?", (property_id,))
                all_rows = cursor.fetchall()
            
                for row in all_rows:
                    #if self.DEBUG:
                    #    print('date: {0}, value: {1}'.format(row[0],row[1]))
                    result.append( {'date':row[0],'value':row[1]} )
                
            else:
                result = []
            
            #if self.DEBUG:
            #    print("log data after point_delete: " + str(result))
            db.close()
            return result
    
        except Exception as e:
            #if self.DEBUG:
            #    print("Error deleting a point: " + str(e))
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
                    print("log file: " + str(fname))
                    if fname.startswith("run-app.log.") and fname != "run-app.log":
                        print("- might delete this file")
                        if filename == "all":
                            try:
                                os.remove(os.path.join(self.log_dir_path, fname))
                                if self.DEBUG:
                                    print("File deleted")
                            except Exception as ex:
                                if self.DEBUG:
                                    print("Could not delete file: " + str(ex))
                        elif str(filename) == str(fname):
                            if self.DEBUG:
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
                if fname.startswith("run-app.log.") and fname != "run-app.log":
                    result.append(fname)
                        
                        
        except Exception as ex:
            if self.DEBUG:
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
            # TODO: add timeout? Switch to bluetoothctl?
            #sudo timeout -s SIGINT 5s hcitool -i hci0 lescan > file.txt
            
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
            if self.DEBUG:
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
                
                #if self.DEBUG:
                #    print("print_test: printer is connected. Printing Hello World.")
                #    self.printer.printBreak(1)
                #else:
                #    self.printer.writeASCII('Hello World\n')
                #    self.printer.printBreak(100)
                return True
            
        except Exception as ex:
            print("testprint error: " + str(ex))
        
        return False
        
        
        
    def print_now(self):
        
        try:
            
            if 'printer_log' in self.persistent_data and 'printer_log_name' in self.persistent_data and 'printer_interval' in self.persistent_data and 'printer_rotation' in self.persistent_data and self.persistent_data['printer_mac'] != '': # and 'printer_interval' in self.persistent_data:
                
                if self.persistent_data['printer_interval'] == 'none':
                    #print("interval is none! Should not print")
                    return {'state':'error','message':'interval is disabled'}
                
                self.get_logs_list()
                
                print_time = int(time_module.time()) # used to remember up until what moment data should be deleted later on
                if self.DEBUG:
                    print("print time: " + str(print_time))
                    print("log ID: " + str(self.persistent_data['printer_log']) + " = " + str(self.persistent_data['printer_log_name']))
                    #print("lookup table: " + str(self.data_types_lookup_table))
                
                try:
                    log_data_type = self.data_types_lookup_table[ int(self.persistent_data['printer_log']) ]
                except Exception as ex:
                    #print("could not lookup log data type. Maybe no data?")
                    return {'state':'error','message':'No data to print'}
                
                if self.DEBUG:
                    print("Log data type: " + str(log_data_type))
                
                
                log_data = self.get_property_data(self.persistent_data['printer_log'], log_data_type)
                if self.DEBUG:
                    print(str(log_data))
                    print("log_data type: " + str(type(log_data)))
                    
                if isinstance(log_data, list): #dict
                    log_data_length = len(log_data)
                    if self.DEBUG:
                        print("initial log length: " + str(log_data_length))
                    
                    if log_data_length > 1:
                        
                        
                        # Prune to log data if it's too much to create a davaviz from.
                        pruned_log_data = []
                        counter = 0
                        if log_data_length > 600:
                            skip_factor = round( len(log_data) / 600 )
                        
                            
                            for log_item in log_data:
                                
                                if counter == 0:
                                    #print("pruning: adding at counter 0")
                                    pruned_log_data.append({'date':log_item['date'], 'value':log_item['value']})
                                elif counter == len(log_data) - 1:
                                    #print("pruning: adding at counter end")
                                    pruned_log_data.append({'date':log_item['date'], 'value':log_item['value']})
                                else:
                                    if counter % skip_factor == 0:
                                        #print("pruning adding at interval: " + str(counter))
                                        pruned_log_data.append({'date':log_item['date'], 'value':log_item['value']})
                            
                                counter += 1
                                
                                    
                            
                            log_data = pruned_log_data
                            log_data_length = len(log_data)
                            if self.DEBUG:
                                print("pruned log length: " + str(log_data_length))
                        
                        
                        self.date_string_to_print = "" # a single line of text printed above the image, or as part of the image
                        
                        counter = 0
                        values = []
                        time_values = []
                        date_objects_array = []
                        time_objects_array = []
                        
                        skippy = round( len(log_data) / 6 )
                        
                        date_objects_pruned = []
                        time_objects_pruned = []
                        #print("log length: " + str(len(log_data)))
                        
                        for log_item in log_data:
                            #print(str(counter))
                            
                            #print(str(log_item))
                            d = round(log_item['date']/1000)
                            v = log_item['value']
                            #print(str(date) + " -> " + str(value))
                            #values.append(value)
                            
                            
                            date_object = datetime.fromtimestamp(d)
                            date_objects_array.append( date_object )
                            time_object = time(date_object.hour ,date_object.minute)
                            time_objects_array.append( time_object )
                            #if counter == 0:
                            #    start = date
                            #if counter == 20:
                            #    print("breaking out of values loop")
                            #    break
                        
                            if counter == 0:
                                #print("adding at counter 0")
                                date_objects_pruned.append(date_object)
                                time_objects_pruned.append(time_object)
                            elif counter == len(log_data) - 1:
                                #print("adding at counter end")
                                date_objects_pruned.append(date_object)
                                time_objects_pruned.append(time_object)
                            else:
                                if counter % skippy == 0:
                                    #print("adding time_object at counter: " + str(counter))
                                    date_objects_pruned.append(date_object)
                                    time_objects_pruned.append(time_object)
                        
                        
                            values.append( (date_object,v) )
                            time_values.append( (time_object,v) )
                            
                            counter += 1
                            
                            
                        #x_label_rotation = 45
                        
                        # How wide should the image be to accomodate all the data points?
                        dataviz_width = 304
                        if len(values) > 152:
                            dataviz_width = len(values) * 2
                            
                        if self.DEBUG:
                            print("dataviz width: " + str(dataviz_width))

                        
                        print_rotation = self.persistent_data['printer_rotation']
                        
                        if print_rotation == 'auto':
                            if dataviz_width > 1000:
                                if self.DEBUG:
                                    print("forcing rotation for log because it has so much data in it")
                                print_rotation = 270
                            else:
                                print_rotation = 0
                                
                        else:
                            print_rotation = int(self.persistent_data['printer_rotation'])
                        
                        
                        

                        dataviz_height = 304
                        if print_rotation == 0 or print_rotation == 180:
                            dataviz_height = 200

                            
                        #dataviz_width = dataviz_width * 2
                        #dataviz_height = dataviz_height * 2


                        # add the data to the log
                        dateline = pygal.DateLine()
                        dateline.add('',values)
                        
                            
                        custom_style = Style(
                          background='#fff',
                          #title_font_size='3',
                          #label_font_size='20',
                          major_label_font_size='24',
                          value_label_font_size='24')
                          
                        dateline.style = custom_style
                            
                        dateline.show_legend = False
                        dateline.human_readable = True
                        #dateline.x_label_rotation = 10
                        #dateline.interpolate = 'hermite'
                        
                        dateline.width = dataviz_width
                        dateline.height = dataviz_height
                        dateline.show_x_labels = False
                        if self.DEBUG:
                            print("dateLine init done")
                        
                        if self.should_print_log_name:
                            dateline.title = self.persistent_data['printer_log_name']
                        
                        #pygal_config = pygal.Config()
                        #pygal_config.show_legend = False
                        #pygal_config.human_readable = True
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        # Creating date/time labels
                        try:
                            #print("log_data[0] = " + str(log_data[0]))
                            log_start_timestamp = round( log_data[0]['date']/ 1000) #round( values[0][0] / 1000)
                            log_end_timestamp = round( log_data[len(log_data)-1]['date']/ 1000) #round( values[len(values)-1][0] / 1000)
                            #print("X")
                            #print("first log date: " + str(log_start_timestamp))
                            #print("last log date: " + str(log_end_timestamp))
                            #print("X")
                            millisecs = [x['date'] for x in log_data]
                            vals = [x['value'] for x in log_data]
                            
                            minimum_value = min( vals )
                            maximum_value = max( vals )
                            #print("maximum value: " + str(maximum_value))
                            
                            #delta_minutes = round((millisecs[len(millisecs)-1] - millisecs[0]) / 60000)
                            delta_minutes = round((log_end_timestamp - log_start_timestamp) / 60)
                            if self.DEBUG:
                                print("delta minutes: " + str(delta_minutes))
                            
                            
                            
                            """
                                
                            # HOURLY LABELS
                            if self.persistent_data['printer_interval'] == 'hourly' and delta_minutes < 60 and int(time_module.strftime("%m")) == 0: #and delta_minutes > 55
                                print("HOUR: " + str( time_module.strftime("%H") ))
                                
                                current_hour = int(time_module.strftime("%H"))
                                previous_hour = int(current_hour - 1)
                                if current_hour == 0:
                                    previous_hour = 23
                                
                                print(str(current_hour))
                                print(str(previous_hour))
                                #dateline.x_labels = [str(previous_hour), ':15', ':30',':45', str(current_hour)] #map(str, range(2002, 2013))
                                
                                #dateline.x_labels = [datetime.fromtimestamp(log_start_timestamp), datetime.fromtimestamp(log_end_timestamp)] #map(str, range(2002, 2013))
                                
                                self.date_string_to_print = current_hour + "h  -  " + current_hour + "h"
                                dateline.x_title = self.date_string_to_print
                                
                                
                                right_now = datetime.now()
                                hour_ago  = right_now - timedelta(hours = 1)
                                
                                dateline.x_labels = [hour_ago, right_now]
                                dateline.x_value_formatter=lambda dt: dt.strftime('%M:%S')
                                
                                #dateline.x_labels_major = [str(previous_hour), str(current_hour)]
                                #dateline.x_label_rotation = 0
                                
                                
                                
                                
                                
                            
                            # DAILY LABELS
                            elif self.persistent_data['printer_interval'] == 'daily' and delta_minutes < 1450: #and delta_minutes > 1350 
                                
                                #dateline.x_labels = map(str, range(0, 24))
                                #dateline.x_label_rotation = 0
                                try:
                                    today = date.today()
                                    yesterday = today - timedelta(days = 1)
                                    self.date_string_to_print = yesterday.strftime("%d %B, %Y") #.strftime("%Y%m%d")
                                except Exception as ex:
                                    print("error creating daily date string")
                            
                            
                            # WEEKLY LABELS
                            elif self.persistent_data['printer_interval'] == 'weekly' and delta_minutes > 10000 and delta_minutes < 10180:
                                dateline.x_labels = ['m ','t ','w ','t ','f ','s ','s ']
                                #dateline.x_label_rotation = 0
                                try:
                                    today = date.today()
                                    week_ago = today - timedelta(days = 7)
                                    self.date_string_to_print = week_ago.strftime("%d %B, %Y") + "  ->  " + yesterday.strftime("%d %B, %Y") #.strftime("%Y%m%d")
                                except Exception as ex:
                                    print("error creating weekly date string")
                            
                            
                            """
                                
                            #else:
                            #elif delta_minutes < 1441:
                            #print("Data is for less than a day, but not a complete hour")
                            
                            log_start_date = datetime.fromtimestamp(log_start_timestamp)
                            #log_start_date2 = log_start_date.replace(tzinfo=timezone.utc)
                            log_end_date = datetime.fromtimestamp(log_end_timestamp)
                            #log_end_date2 = log_end_date.replace(tzinfo=timezone.utc)
                            
                            #print("log_start hour and minute: " + str( log_start_date.strftime("%H:%M") ))
                            #print("log_start hour and minute2: " + str( log_start_date2.strftime("%H:%M") ))
                            #print("log_end hour and minute: " + str( log_end_date.strftime("%H:%M") ))
                            #print("log_end hour and minute2: " + str( log_end_date2.strftime("%H:%M") ))
                            #dateline.x_labels = [log_start_date.strftime("%H:%M"),log_end_date.strftime("%H:%M")]
                            
                            dateline.x_label_rotation = 30
                            
                            dateline.truncate_label = -1
                            dateline.x_labels = date_objects_array
                            dateline.x_labels_major = [log_start_date,log_end_date] # date_objects_pruned #map(lambda d: d.strftime('%H:%M'), date_objects_pruned)
                            
                            dateline.show_minor_x_labels = False # in the end decided to mostly just print the date and time above the image, it's simpler and takes less space.
                            
                            if delta_minutes < 1441:
                                self.date_string_to_print = log_start_date.strftime("%d %B, %Y -   %H:%M") + "  to  " + log_end_date.strftime("%H:%M") + ""
                                #dateline.x_title = self.date_string_to_print
                                #self.date_string_to_print = ""
                            else:
                                self.date_string_to_print = log_start_date.strftime("%H:%M  %d %B, %Y") + "  to  " + log_end_date.strftime("%H:%M  %d %B, %Y ") + ""
                                                   
                                
                                
                            
                                
                                
                                #experi = [log_start_date.strftime('%H:%M')]
                                #for x in range( len(values) - 2 ):
                                #    experi.append(None)
                                #experi.append(log_end_date.strftime('%H:%M'))
                                #print("created experi")
                                #dateline.x_labels = map(lambda d: d.strftime('%H:%M'), date_objects_array)
                                #dateline.x_labels = map(lambda d: d.strftime('%H:%M'), experi)
                                #dateline.x_labels = map(str, time_objects_array)
                                #dateline.x_value_formatter = lambda dt: dt.strftime('%M:%S')
                                #dateline.x_labels = map(str, time_objects_pruned)
                                #dateline.x_labels = map(str, date_objects_pruned)
                                #dateline.x_value_formatter = lambda dt: dt.strftime('%M:%S')
                                #dateline.x_label_formatter = lambda dt: dt.strftime('%M:%S')
                                
                                #dateline.x_labels = map(lambda d: d.strftime('%H:%M'), date_objects_pruned)
                                
                                #dateline.x_labels = map(str, [datetime.fromtimestamp(log_start_timestamp), datetime.fromtimestamp(log_end_timestamp)])
                                #dateline.x_labels = [datetime.fromtimestamp(log_start_timestamp), datetime.fromtimestamp(log_end_timestamp)]
                                
                                
                                
                                #print("x labels added")
                                
                                #dateline.add('Here is axvspan', [(log_start_date, minimum_value), (log_end_date, maximum_value)])
                                
                                
                                
                                #dateline.x_value_formatter=lambda dt: dt.strftime('%d, %b %Y at %I:%M:%S %p')
                                
                                #print("formatter added")
                                #dateline.show_minor_x_labels = False
                                #dateline.x_labels_major_every = len(date_objects_array) - 1
                                #dateline.x_labels_major = [str(log_start_date.strftime("%H:%M")), str(log_end_date.strftime("%H:%M"))]
                                #dateline.x_labels_major = [log_start_date, log_end_date]
                            
                            #else:
                                # by default the dates will be shown
                            #    print("default dates will be shown")
                            #    pass
                            
                        except Exception as ex:
                            print("error creating time labels: " + str(ex))
                        
                        

                        
                        

                        

                        

                        dateline.margin_top = 0
                        dateline.margin_right = 0
                        dateline.margin_bottom = 0
                        dateline.show_x_guides = True
                        dateline.render_to_png(self.chart_png_file_path)
                        
                        #time.sleep(.1)
                        
                        if os.path.exists(self.chart_png_file_path) is False:
                            if self.DEBUG:
                                print("Error: chart image file was not generated")
                            return {'state':'error','message':'The image to be printed could not be generated'}
                        
                        
                        else:
                            if self.DEBUG:
                                print("DateLine dataviz generated.")
                                
                            printed = self.print_image_file(self.chart_png_file_path, print_rotation)
                            
                            if printed:
                                if self.DEBUG:
                                    print("Graph was printed. Deleting data points.")
                                if self.do_not_delete_after_printing == False:
                                    if self.DEBUG:
                                        print("about to delete data, since print was successful (if the paper hasn't run out...)")
                                    self.point_delete(self.persistent_data['printer_log'],log_data_type,0, print_time * 1000 ) # deletes all data in the log
                                 # and self.DEBUG == False:
                                
                                return {'state':'ok','message':'Log was printed'}                                   
                                
                            else:
                                if self.DEBUG:
                                    print("Graph was NOT printed")
                                return {'state':'error','message':'Could not connect to printer'}
                                
                        
                    elif log_data_length == 1:
                        print("only one data point in this period")
                        
                        return {'state':'ok','message':'Log only had one datapoint.'}
                        
                    elif log_data_length == 0:
                        if self.DEBUG:
                            print("no data points to print")
                        
                        return {'state':'ok','message':'Log did not contain any data points'}
                
                else:
                    if self.DEBUG:
                        print("Error: log data could not be loaded")
                    return {'state':'error','message':'Log data could not be loaded.'}
            else:
                if self.DEBUG:
                    print("missing parameters")
                return {'state':'error','message':'Missing parameters, could not print. Check and save your settings.'}
            
            
            
        except Exception as e:
            if self.DEBUG:
                print("ERROR in print_now: " + str(e))
            return {'state':'error','message':'General error in print_now: ' + str(e)}



    def connect_to_printer(self):
        if self.DEBUG:
            print("in connect_to_printer")
            
        self.busy_connecting_to_printer = True
        if time_module.time() - self.last_printer_check_time < 5:
            if self.DEBUG:
                print("connected check was already recently performed, skipping doing it again.")
            return self.printer_connected
            
        try:
            if self.printer == None and self.persistent_data['printer_mac'] != '':
                if self.DEBUG:
                    print("creating printer object with mac: " + str(self.persistent_data['printer_mac']))
                self.printer = ppa6.Printer(self.persistent_data['printer_mac'], ppa6.PrinterType.A6p)
                
                #self.printer.setTimeout(8) # seconds for bluetooth connection timeout
                
            if self.printer != None:
                if self.DEBUG:
                    print("printer object exists")
                self.printer_connected = self.printer.isConnected()
                if self.DEBUG:
                    print("self.printer_connected: " + str(self.printer_connected))
                if self.printer_connected == False:
                    if self.DEBUG:
                        print("Printer is not connected. Will attempt to reconnect.")
                    try:
                        self.printer.reconnect()
                        self.printer.reset()
                    except Exception as ex:
                        if self.DEBUG:
                            print("printer.reconnect didn't work, trying connect instead. Error: " + str(ex))
                        try:
                            self.printer.connect()
                            self.printer.reset()
                        except Exception as ex:
                            if self.DEBUG:
                                print("printer.reconnect also didn't work. Error: " + str(ex))
                        
                self.last_printer_check_time = time_module.time()
                        
                
                if self.printer_connected == False:
                    time_module.sleep(1)
                    self.printer_connected = self.printer.isConnected()
                    
                if self.printer_connected:
                    self.printer_connection_counter = 0
                    
                    if self.power_timeout_set == False:
                        self.power_timeout_set = True
                        try:
                            self.printer.setPowerTimeout(300) # minutes. Tells device to stay awake. 300 minutes = 5 hours
                            os.system('sudo bluetoothctl trust ' + str(self.persistent_data['printer_mac']))
                        except Exception as ex:
                            if self.DEBUG:
                                print("setPowerTimeout error: " + str(ex))
                                
                    
                    
                    if self.DEBUG:
                        try:
                            print(f'Name: {self.printer.getDeviceName()}')
                            print(f'S/N: {self.printer.getDeviceSerialNumber()}')
                            print(f'F/W: {self.printer.getDeviceFirmware()}')
                            print(f'Battery: {self.printer.getDeviceBattery()}%')
                            print(f'H/W: {self.printer.getDeviceHardware()}')
                            print(f'MAC: {self.printer.getDeviceMAC()}')
                        except Exception as ex:
                            if self.DEBUG:
                                print("Debug only Error while asking the printer for details: " + str(ex))
                        
                else:
                    if self.DEBUG:
                        print("ERROR, was unable to (re)connect to the printer")
                
                # update thing property
                if self.adapter != None:
                    if 'printer_connected' in self.adapter.thing.properties:
                        self.adapter.thing.properties['printer_connected'].update(self.printer_connected)
                    
            else:
                if self.DEBUG:
                    print("printer has not been set up yet.")
                        
        except Exception as ex:
            print("error setting up printer: " + str(ex))
            self.printer_connected = False

        self.busy_connecting_to_printer = False

        return self.printer_connected


    def print_image_file(self,filename, print_rotation=0):
        try:
            if self.printer.isConnected() == False:
                if self.DEBUG:
                    print("Print_image_file: attempting to (re)connect to printer")
                self.connect_to_printer()
        
            if self.printer.isConnected():
                if self.DEBUG:
                    print("print_now: printer is connected!")
                try:
                    #print(f'Full: {printer.getDeviceFull()}')
                    self.printer_connection_counter = 0
                    
                    printer_contrast_number = 2
                    if self.persistent_data['printer_contrast'] == 'medium':
                        printer_contrast_number = 1
                    elif self.persistent_data['printer_contrast'] == 'low':
                        printer_contrast_number = 0
                    self.printer.setConcentration(printer_contrast_number)
            
            
                    img = None
            
                    try:
                        img = Image.open(filename).convert('RGBA') #self.chart_png_file_path
                
                        if self.DEBUG:
                            print("rotation preference was: " + str(self.persistent_data['printer_rotation']))
                            print("actual print rotation: " + str(print_rotation))
                
                        if print_rotation != 0:
                            if self.DEBUG:
                                print("rotating image")
                            img2 = img.rotate(print_rotation, expand=True)
                        else:
                            img2 = img
                        
                    except Exception as ex:
                        print('Error rotating image: ' + str(ex))

                    # check if image exists.
            
                    if self.date_string_to_print != "":
                        self.printer.writeASCII(self.date_string_to_print + '\n')
                        self.date_string_to_print = ""
                
                    if self.DEBUG:
                        print("Printing log image now")
                    self.printer.printImage(img2, resample=Image.ANTIALIAS)
            
                    if self.DEBUG:
                        print("printing break")
                    self.printer.printBreak(100)
                    
                except Exception as ex:
                    if self.DEBUG:
                        print("Error rotating and printing: " + str(ex))
            
                try:
                    os.remove(filename)
                    if self.DEBUG:
                        print("printed file has been deleted: " + str(filename))
                        
                except Exception as ex:
                    if self.DEBUG:
                        print("Warning, could not delete generated image:" + str(ex))
            
                return True
            
            else:
                if self.DEBUG:
                    print("print_now: error, not connected to printer")
                return False
                
        except Exception as ex:
            print("Error in print_image_file: " + str(ex))
            return False
            


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
            if self.DEBUG:
                print("Error: could not store data in persistent store: " + str(ex) )
                print(str(self.persistent_data))
            return False






#
#  Quick delete thing + filter
#

    # Deletes data from ALL logs for the last few minutes/hours
    def quick_delete_filter(self,duration):
        if self.DEBUG:
            print("in quick delete")
        try:
            if self.DEBUG:
                print("in quick delete filter, with duration: " + str(duration))
        
            self.get_logs_list()
        
            current_time = int(time_module.time()) * 1000
            early_time = current_time - (duration * 60 * 1000) # milliseconds
            if self.DEBUG:
                print("early_time: " + str(early_time))
        
            for log_id, log_data_type in self.data_types_lookup_table.items():
                if self.DEBUG:
                    print("x")
                    print("quick deleting. Log_id: " + str(log_id) + ", data_type: " + str(log_data_type) + ", early_time: " + str(early_time) + ", current_time: " + str(current_time))
                self.point_delete(log_id,log_data_type, early_time, current_time * 1000)
        
            self.adapter.send_pairing_prompt("Deleted the last " + str(duration) + " minutes of log data")
            
        except Exception as ex:
            if self.DEBUG:
                print("error in quick_delete_filter: " + str(ex))



    def duration_name_to_int_lookup(self,duration_string):
        if self.DEBUG:
            print("in duration_name_to_int_lookup. String: " + str(duration_string))
        for key, value in self.duration_lookup_table.items():
            if value == duration_string:
                if self.DEBUG:
                    print("Duration reverse lookup success. Returning: " + str(key))
                return int(key)
        return None


    def get_duration_names_list(self):
        duration_names = []
        for key, value in self.duration_lookup_table.items():
            duration_names.append(value)
        return duration_names


    def thing_delete_button_pushed(self):
        if self.DEBUG:
            print("in thing_delete_button_pushed")
        #self.adapter.send_pairing_prompt("Deleted the last " + "xx" + " minutes of log data")
        self.quick_delete_filter(self.persistent_data['duration'])









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
                time_module.sleep(.1) #Don't waste CPU-cycles
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




