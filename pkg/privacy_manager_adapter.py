
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
        self.api_handler = api_handler
        self._type.append(device_type)
        #self._type = ['OnOffSwitch']

        self.name = device_name
        self.title = device_title
        self.description = 'Control devices via via the internet'

        #if self.adapter.DEBUG:
        #print("Empty PrivacyManager thing has been created. device_name = " + str(self.name))
        #print("new thing's adapter = " + str(self.adapter))

        #print("self.api_handler.persistent_data['enabled'] = " + str(self.api_handler.persistent_data['enabled']))
        
        self.properties["data-deletion"] = PrivacyManagerProperty(
                            self,
                            "data-deletion",
                            {
                                '@type': 'OnOffProperty',
                                'title': "Data deletion",
                                'type': 'boolean',
                                'readOnly': False,
                            },
                            False)

        """
        self.properties["anonymous-id"] = PrivacyManagerProperty(
                            self,
                            "anonymous-id",
                            {
                                'title': "Annymous ID",
                                'type': 'string',
                                'readOnly': True
                            },
                            self.api_handler.persistent_data['uuid'])

        """
        #targetProperty = self.find_property('outside-access')
        #targetProperty.update(self.api_handler.persistent_data['enabled'])

        #print(str(self.properties["outside-access"]))


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
        self.value = False
        self.set_cached_value(False)
        self.device.notify_property_changed(self)
        print("privacy manager property initiated")
        #self.update(value)
        #self.set_cached_value(value)
        #self.device.notify_property_changed(self)
        #print("property initialized")


    def set_value(self, value):
        print("set_value is called on a PrivacyManager property: " + str(self.name) + " With new value: " + str(value))

        try:
            
            if self.name == 'data-deletion':
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
            
            else:
                self.update(value)
            
            #if self.name == "outside-access":
            #    self.device.api_handler.persistent_data['enabled'] = value
            #    self.device.api_handler.save_persistent_data()
            
            
        except Exception as ex:
            print("property:set value:error: " + str(ex))
        

    def update(self, value):
        print("privacy_manager property -> update to: " + str(value))
        #print("--prop details: " + str(self.title) + " - " + str(self.original_property_id))
        #print("--pro device: " + str(self.device))
        if value != self.value:
            self.value = value
            self.set_cached_value(value)
            self.device.notify_property_changed(self)
        
