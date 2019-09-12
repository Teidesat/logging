import time
from datetime import datetime
from threading import Thread
from src.utils.Logger import default_logger as logger
from src.utils.CSVWriter import CSVWriter
from src.services.BaseService import BaseService
from src.sensors.SensorsProvider import SensorsProvider
from pathlib import Path


class MonitorService(BaseService):

    class SensorData:
        def __init__(self, value=None, sensor_id=None, timestamp=None, type=None):
            self.value = value
            self.sensor_id = sensor_id
            self.timestamp = timestamp
            self.type = type

    def __init__(self, simulate=False, period=1000):
        super().__init__(service_name="Monitor")
        Path('./log').mkdir(exist_ok=True)
        self.on_new_sensor_data_listener = None
        self.__simulate = simulate
        self.__period = float(period)
        self.__sensors_data = [] # TODO wouldnt this fill the memory eventually ?
        self.__csv_file = CSVWriter('log/' + datetime.now().strftime('%Y-%m-%d_%H%M%S') + '_sensors_data.csv')
        self.__csv_file.write_row(['timestamp', 'sensor_id', 'type;value'])
        self.__sensors = SensorsProvider.get_available_sensors(self.__simulate)
        self.__last_time = 0

    def get_sensors_data(self):
        return self.__sensors_data

    def get_last_sensors_data(self):
        # TODO use lock to prevent race conditions
        """
        Data is saved in the sensors in order. We just need to retrieve the last
        n data points, where n is the number of sensors.
        """
        if len(self.__sensors) == 0 or len(self.__sensors_data) < len(self.__sensors):
            return None
        return self.__sensors_data[-len(self.__sensors):]

    def get_last_sensor_data(self):
        return self.__sensors_data[-1] if len(self.__sensors_data) > 0 else None

    def register_new_sensor_data(self, sensor_data):
        log_msg = 'SENSOR DATA: timestamp: %s, sensor_id: %s, type: %s' % (sensor_data.timestamp, sensor_data.sensor_id, sensor_data.type)

        if type(sensor_data.value) is list:
            log_msg += ', values: %s' % ', '.join('{:0.3f}'.format(i) for i in sensor_data.value)
        elif type(sensor_data.value) is float:
            log_msg += ', value: %.3f' % sensor_data.value
        else:
            logger.warn('Invalid value format retrieved from sensor %s' % sensor_data.sensor_id)
            log_msg += ', value: INVALID VALUE'

        logger.debug(log_msg)
        self.__sensors_data.append(sensor_data)
        self.__csv_file.write_row([sensor_data.timestamp, sensor_data.sensor_id, sensor_data.type, sensor_data.value])
        if self.on_new_sensor_data_listener is not None:
            self.on_new_sensor_data_listener(sensor_data)

    def service_run(self):
        if (time.time() - self.__last_time) * 1000 >= self.__period:
            self.__last_time = time.time()
            for sensor in self.__sensors:
                sensor_data = MonitorService.SensorData()
                try:
                    sensor_data.value = sensor.get_value()
                except:
                    logger.warn('Error while trying to read the sensor \'%s\'' % sensor.get_id())
                    sensor_data.value = None
                sensor_data.sensor_id = sensor.get_id()
                sensor_data.type = sensor.get_type()
                sensor_data.timestamp = int(round(time.time() * 1000))

                if sensor_data.value is None:
                    sensor_data.value = -999.0
                elif type(sensor_data.value) is list:
                    sensor_data.value = [-999.0 if v is None else v for v in sensor_data.value]

                self.register_new_sensor_data(sensor_data)
        else:
            time.sleep(0.05)
