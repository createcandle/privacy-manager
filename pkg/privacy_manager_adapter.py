
from time import sleep

try:
    from gateway_addon import Adapter, Device, Property
    #print("succesfully loaded APIHandler and APIResponse from gateway_addon")
except:
    print("Could not load vital libraries to interact with the controller")


#
#  ADAPTER
#        

class PrivacyManagerAdapter(Adapter):
    """Adapter that can hold and manage things"""

    def __init__(self, api_handler, verbose=False):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """

        self.api_handler = api_handler
        self.name = self.api_handler.addon_name #self.__class__.__name__
        #print("adapter name = " + self.name)
        self.adapter_name = self.api_handler.addon_name #'PrivacyManager-adapter'
        Adapter.__init__(self, self.adapter_name, self.adapter_name, verbose=verbose)
        self.DEBUG = self.api_handler.DEBUG
        
        try:
            # Create the thing
            privacy_manager_device = PrivacyManagerDevice(self,api_handler,"privacy_manager","Privacy Manager","OnOffSwitch")
            self.handle_device_added(privacy_manager_device)
            self.devices['privacy_manager'].connected = True
            self.devices['privacy_manager'].connected_notify(True)
            self.thing = self.get_device("privacy_manager")
            
            print("adapter: self.ready?: " + str(self.ready))
        
        except Exception as ex:
            print("Error during privacy manager adapter init: " + str(ex))


    def remove_thing(self, device_id):
        if self.DEBUG:
            print("Removing privacy_manager thing: " + str(device_id))
        
        try:
            obj = self.get_device(device_id)
            self.handle_device_removed(obj)                     # Remove from device dictionary

        except Exception as ex:
            print("Could not remove thing from PrivacyManager adapter devices: " + str(ex))
            
            
        
        


#
#  DEVICE
#

class PrivacyManagerDevice(Device):
    """PrivacyManager device type."""

    def __init__(self, adapter, api_handler, device_name, device_title, device_type):
        """
        Initialize the object.
        adapter -- the Adapter managing this device
        """

        
        Device.__init__(self, adapter, device_name)
        #print("Creating PrivacyManager thing")
        
        self._id = device_name
        self.id = device_name
        self.adapter = adapter
        self.api_handler = self.adapter.api_handler
        self._type.append(device_type)
        #self._type = ['OnOffSwitch']

        self.name = device_name
        self.title = device_title
        self.description = 'Control devices via via the internet'

        #if self.adapter.DEBUG:
        #print("Empty PrivacyManager thing has been created. device_name = " + str(self.name))
        #print("new thing's adapter = " + str(self.adapter))

        #print("self.api_handler.persistent_data['enabled'] = " + str(self.api_handler.persistent_data['enabled']))
        
        self.properties["data_deletion"] = PrivacyManagerProperty(
                            self,
                            "data_deletion",
                            {
                                '@type': 'OnOffProperty',
                                'title': "Data deletion",
                                'type': 'boolean',
                                'readOnly': False,
                            },
                            False)

                            
        
        duration_strings_list = self.adapter.api_handler.get_duration_names_list()
        if self.adapter.DEBUG:
            print("Creating property. Duration_strings_list: " + str(duration_strings_list))
        
        duration_string = duration_strings_list[0]
        try:
            if 'duration' in self.adapter.api_handler.persistent_data:
                duration_string = self.adapter.api_handler.duration_lookup_table[ str(self.adapter.api_handler.persistent_data['duration']) ]
                #print("duration string lookup succeeded? Duration string is now: " + str(duration_string))
        except Exception as ex:
            print("Error looking up duration in table: " + str(ex))

        if self.adapter.DEBUG:
            print("initial duration string for thing property: " + str(duration_string))

        self.properties["data_deletion_duration"] = PrivacyManagerProperty(
                        self,
                        "data_deletion_duration",
                        {
                            'title': "Time span",
                            'type': 'string',
                            'enum': duration_strings_list  #["1 minute","10 minutes","30 minutes","1 hour","2 hours","4 hours","8 hours"]
                        },
                        duration_string)


        if self.api_handler.persistent_data['printer_mac'] != '':
            self.properties["printer_connected"] = PrivacyManagerProperty(
                            self,
                            "printer_connected",
                            {
                                'title': "Printer state",
                                'type': 'boolean',
                                'readOnly': True
                            },
                            self.api_handler.printer_connected)

            self.properties["printer_battery"] = PrivacyManagerProperty(
                            self,
                            "printer_battery",
                            {
                                'title': "Printer battery level",
                                'type': 'integer',
                                'minimum': 0,
                                'maximum': 100,
                                'unit': 'percent',
                                'readOnly': True
                            },
                            self.api_handler.printer_connected)

            
            self.properties["printer_contrast"] = PrivacyManagerProperty(
                            self,
                            "printer_contrast",
                            {
                                'title': "Printer contrast",
                                'type': 'string',
                                'enum': ['low','medium','high']
                            },
                            self.api_handler.persistent_data['printer_contrast'])
            


#
#  PROPERTY
#


class PrivacyManagerProperty(Property):
    """PrivacyManager property type."""

    def __init__(self, device, name, description, value):
        Property.__init__(self, device, name, description)
        
        #print("new property with value: " + str(value))
        self.device = device
        self.name = name
        self.title = name
        self.description = description # dictionary
        self.value = value
        self.set_cached_value(value)
        self.device.notify_property_changed(self)
        if self.device.adapter.DEBUG:
            print("privacy manager property initiated: " + str(self.name) + ", with value: " + str(self.value))
        #self.update(value)
        #self.set_cached_value(value)
        #self.device.notify_property_changed(self)
        #print("property initialized")


    def set_value(self, value):
        if self.device.adapter.DEBUG:
            print("set_value is called on a PrivacyManager property: " + str(self.name) + ", with new value: " + str(value))

        try:
            
            if self.name == 'data_deletion':
                self.value = True
                self.set_cached_value(value)
                self.device.notify_property_changed(self)
                
                self.device.api_handler.thing_delete_button_pushed()
                #self.update(True)
                #self.update(False)
                #self.set_cached_value(True)
                #self.device.notify_property_changed(self)
                sleep(4)
                self.value = False
                self.set_cached_value(False)
                self.device.notify_property_changed(self)
            
            elif self.name == 'data_deletion_duration':
                if self.device.adapter.DEBUG:
                    print("incoming data_deletion_duration enum string: " + str(value))
                self.device.adapter.api_handler.persistent_data['duration'] = self.device.adapter.api_handler.duration_name_to_int_lookup(str(value))
                if self.device.adapter.DEBUG:
                    print("self.device.adapter.api_handler.persistent_data['duration'] is now: " + str(self.device.adapter.api_handler.persistent_data['duration']))
                self.update(value)
                
            elif self.name == 'printer_contrast':
                options = ['low','medium','high']
                if str(value) in options:
                    self.device.adapter.api_handler.persistent_data['printer_contrast'] = str(value)
                    self.update(value)
                
            else:
                self.update(value)
            
            #if self.name == "outside-access":
            #    self.device.api_handler.persistent_data['enabled'] = value
            #    self.device.api_handler.save_persistent_data()
            
            
        except Exception as ex:
            print("property:set value:error: " + str(ex))
        

    def update(self, value):
        if self.device.adapter.DEBUG:
            print("privacy_manager property -> update to: " + str(value))
        #print("--prop details: " + str(self.title) + " - " + str(self.original_property_id))
        #print("--pro device: " + str(self.device))
        if value != self.value:
            self.value = value
            self.set_cached_value(value)
            self.device.notify_property_changed(self)
        
