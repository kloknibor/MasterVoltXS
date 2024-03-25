"""
Support for displaying the current solar power produced.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.xxxx/
"""
import socket
import struct
import http.client, urllib
import time, datetime
import asyncio

import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorStateClass, SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity import Entity
from homeassistant.core import CoreState
from homeassistant.const import UnitOfEnergy
from homeassistant.util.dt import utc_from_timestamp

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['XSsolar==0.8']

CONF_TCP_IP = 'TCP_IP'
CONF_TCP_PORT = 'TCP_PORT'
CONF_RECONNECT_INTERVAL = 'RECONNECT_INTERVAL'
reconnectInterval = 10

ICON = 'mdi:pulse'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TCP_IP): cv.string,
    vol.Required(CONF_TCP_PORT): cv.port,
    vol.Required(CONF_RECONNECT_INTERVAL): int,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the SunMasterXS sensor."""
    # Mapping all the outcome values to a sensor
    Sensor_mappings = [
        [
            'VDc_Solar',
            'V'
        ],
        [
            'IDc_Solar',
            'A'
        ],
        [
            'PDc_Solar',
            'W'
        ],
        [
            'Freq_Solar',
            'Hz'
        ],
        [
            'VAc_Solar',
            'V'
        ],
        [
            'IAc_Solar',
            'A'
        ],
        [
            'PAc_Solar',
            'W'
        ],
        [
            'Temp_Solar',
            '°C'
        ],
        [
            'Runtime_Solar',
            'm'
        ],
    ]

    #make array with all the values it will output
    devices = [SunMasterXSSensor(name, unit_of_measurement) for name, unit_of_measurement in Sensor_mappings]
    devices.append(SunMasterXSSensorEnergy("Wtot_Solar"))

    #adding all the devices
    async_add_entities(devices)

    #getting parameters from config file
    TCP_IP = config[CONF_TCP_IP]
    TCP_PORT = config[CONF_TCP_PORT]
    RECONNECT_INTERVAL = config[CONF_RECONNECT_INTERVAL]

    def update_entities(data):
        """Update entities with latest telegram and trigger state update."""
        # Make all device entities aware of new data
        for device in devices:
            if(device._name == 'VDc_Solar'):
                device._state = data['dcv']
            elif(device._name == 'IDc_Solar'):
                device._state = data['dci']
            elif(device._name == 'PDc_Solar'):
                device._state = data['dcp']
            elif(device._name == 'Freq_Solar'):
                device._state = data['freq']
            elif(device._name == 'VAc_Solar'):
                device._state = data['acv']
            elif(device._name == 'IAc_Solar'):
                device._state = data['aci']
            elif(device._name == 'PAc_Solar'):
                device._state = data['acp']
            elif(device._name == 'Wtot_Solar') and (data['totalpower'] > 0):
                if device._state == None:
                    device._state = data['totalpower']
                else:
                    if device._state <= data['totalpower']:
                        device._state = data['totalpower']

            elif(device._name == 'Temp_Solar'):
                device._state = data['temp']
            elif(device._name == 'Runtime_Solar') and (data['totalruntime'] > 0):
                device._state = data['totalruntime']

        hass.async_create_task(device.async_update_ha_state(force_refresh=True))

    async def update():
        """Get the latest data and updates the state."""
        from XSsolar import Inverter
        from XSsolar import RequestC1
        from XSsolar import Read

        while hass.state != CoreState.stopping:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)

            try:
                s.connect((TCP_IP, TCP_PORT)) # connect to tcp-converter
            except:
                _LOGGER.error("Unable to connect to tcp converter" )
                await asyncio.sleep(reconnectInterval)
                # quit & throttle reconnect attempts
            else:
                # "flush":
                while (1):
                    try:
                        chunk = s.recv(1) # block untill timeout
                    except:
                        break

                # send the first command, to discover all connected inverters
                rq = RequestC1()
                rq.send(s)
                responses = Read(s)

                # get inverters from response
                inverters = []
                invertorCounter = 0
                for r in responses:
                    if (r.type == 193):
                        i = Inverter(r.address,s)
                        inverters.append(i)
                        invertorCounter += 1
                    else:
                        _LOGGER.error("Response type does not match request C1")

                # go get values from inverters
                data = {}
                if (invertorCounter > 1):
                    _LOGGER.error("Sotware only supports 1 invertor, only showing last one")
                if (invertorCounter == 0):
                    data['dcv'] = 0
                    data['dci'] = 0
                    data['freq'] = 0
                    data['acv'] = 0
                    data['aci'] = 0
                    data['acp'] = 0
                    data['totalpower'] = 0
                    data['temp'] = 0
                    data['totalruntime'] = 0
                    data['dcp'] = 0
                    _LOGGER.info("No invertor found, maybe shutoff")
                else:
                    for i in inverters:
                        try:
                            i.getRunningValues() # get running values for this moment
                            if (i.values['errors'] < 32768):
                                _LOGGER.error("error in inverter : %s", i.values['errors'])
                                data['dcv'] = 0
                                data['dci'] = 0
                                data['freq'] = 0
                                data['acv'] = 0
                                data['aci'] = 0
                                data['acp'] = 0
                                data['totalpower'] = 0
                                data['temp'] = 0
                                data['totalruntime'] = 0
                                data['dcp'] = 0
                            else:
                                data['dcv'] = i.values['dcv']
                                data['dci'] = i.values['dci']
                                data['freq'] = i.values['freq']
                                data['acv'] = i.values['acv']
                                data['aci'] = i.values['aci']
                                data['acp'] = i.values['acp']
                                data['totalpower'] = i.values['totalpower']
                                data['temp'] = i.values['temp']
                                data['totalruntime'] = i.values['totalruntime']
                                data['dcp'] = i.values['dcv'] * i.values['dci']
                        except Exception as e:
                            _LOGGER.error("Data transfer incomplete, maybe inverter shutdown during data transfer" )
                            _LOGGER.error("exception : %s", e)
                            data['dcv'] = 0
                            data['dci'] = 0
                            data['freq'] = 0
                            data['acv'] = 0
                            data['aci'] = 0
                            data['acp'] = 0
                            data['totalpower'] = 0
                            data['temp'] = 0
                            data['totalruntime'] = 0
                            data['dcp'] = 0

                s.close()
                update_entities(data)


                # throttle reconnect attempts
                await asyncio.sleep(reconnectInterval)

    hass.loop.create_task(update())

class SunMasterXSSensor(Entity):
    """Representation of a Sunmaster XS sensor."""

    def __init__(self, name, unit_of_measurement ):
        """Initialize the sensor."""
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON


class SunMasterXSSensorEnergy(SensorEntity):
    """Representation of a Sunmaster XS sensor for the homeassistant energy component."""

    def __init__(self, name):
        """Initialize the sensor."""
        self._name = name
        self._state = None
        _LOGGER.info("MastervoltXS integration initialized")

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def unit_of_measurement(self):
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def state_class(self):
        """used by Metered entities / Long Term Statistics"""
        return SensorStateClass.TOTAL_INCREASING
