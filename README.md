This home assistant sensor is to read info from the XS Mastervolt invertors from a serial to ethernet/wifi converter and is only tested with:
- XS2000
- XS3200

To install this sensor add the MasterVolt.py file to the  this add the following to your configuration.yaml :

## Installation of the custom component

* Copy the content of MasterVolt.py into your ```custom_components/sensor``` folder, which is a subdirectory of your Home Assistant configuration directory. By default, this directory is located under ```~/.home-assistant```. 

* Enable the new sensor in your ```configuration.yaml```:

```
sensor:
  - platform: MasterVoltXS
    TCP_PORT: 5678
    TCP_IP: 192.168.1.173
    RECONNECT_INTERVAL: 10
```

All field are required.

* Restart Home Assistant.

Done. If you follow all the instructions, the Mastervolt integration should be up and running.
