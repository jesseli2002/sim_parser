import os
import subprocess as sp
import threading
import struct
from enum import Enum
from pathlib import Path
import typing

# from .hw_sim import SensorType
from stream_filter import ReadFilter, WriteFilter


class LoggerMock:
    def info(self, *args):
        print(*args)

    def debug(self, *args):
        print(*args)

    def exception(self, *args):
        print(*args)
        raise RuntimeError


LOGGER = LoggerMock()


class SimRxId(Enum):
    CONFIG = 0x01
    BUZZER = 0x07
    DIGITAL_PIN_WRITE = 0x50
    RADIO = 0x52
    ANALOG_READ = 0x61
    SENSOR_READ = 0x73
    TIME_UPDATE = 0x74


class SimTxId(Enum):
    RADIO = 0x52
    ANALOG_READ = 0x61
    SENSOR_READ = 0x73
    TIME_UPDATE = 0x74


LOG_HISTORY_SIZE = 500

# ID_TO_SENSOR = {
#     0x00: SensorType.GPS,
#     0x01: SensorType.IMU,
#     0x02: SensorType.ACCELEROMETER,
#     0x03: SensorType.BAROMETER,
#     0x04: SensorType.TEMPERATURE,
#     0x05: SensorType.THERMOCOUPLE,
# }


class SimReadParser:
    def __init__(self, stdout: typing.BinaryIO):
        self.callback = None
        self.bigEndianInts = None
        self.bigEndianFloats = None

        self.stdout = ReadFilter(stdout, LOG_HISTORY_SIZE)
        self.device_address = "<log_replay>"

        # Gets endianess of ints and floats
        self._getEndianness()

        # self._xbee = XBeeModuleSim(bytes.fromhex(gs_address))
        # self._xbee.rocket_callback = self._send_radio_sim
        # self._hw_sim = hw_sim

        self._shutdown_lock = threading.RLock()
        self._is_shutting_down = False

        self._run()

    def send(self, device_address, data):
        # ????
        print(f"Requesting send to devaddr={device_address} : {data}")

    # def _send_radio_sim(self, data):
    #     self._send_sim_packet(SimTxId.RADIO.value, data)

    # def registerCallback(self, fn):
    #     self.callback = fn
    #     self._xbee.ground_callback = self._receive

    # def _receive(self, data):
    #     if not self.callback:
    #         raise Exception("Can't receive data. Callback not set.")

    #     message = ConnectionMessage(
    #         device_address=self.device_address, connection=self, data=data
    #     )

    #     self.callback(message)

    # Returns whether ints should be decoded as big endian
    def isIntBigEndian(self):  # must be thead safe
        assert self.bigEndianInts is not None
        return self.bigEndianInts

    # Returns whether floats should be decoded as big endian
    def isFloatBigEndian(self):
        assert self.bigEndianFloats is not None
        return self.bigEndianFloats

    def shutdown(self):
        with self._shutdown_lock:
            self._is_shutting_down = True

        self._xbee.shutdown()
        self._hw_sim.shutdown()

    # AKA handle "Config" packet
    def _getEndianness(self):
        id = self.stdout.read(1)[0]
        assert id == SimRxId.CONFIG.value

        length = self._getLength()
        assert length == 8
        data = self.stdout.read(length)

        self.bigEndianInts = data[0] == 0x04
        self.bigEndianFloats = data[4] == 0xC0

        LOGGER.info(
            f"SIM: Big Endian Ints - {self.bigEndianInts}, Big Endian Floats - {self.bigEndianFloats} (device_address={self.device_address})"
        )

    def _handleBuzzer(self):
        length = self._getLength()
        assert length == 1
        data = self.stdout.read(length)

        songType = int(data[0])
        LOGGER.info(
            f"SIM: Bell rang with song type {songType} (device_address={self.device_address})"
        )

    def _handleDigitalPinWrite(self):
        length = self._getLength()
        assert length == 2
        pin, value = self.stdout.read(2)

        LOGGER.info(
            f"SIM: Pin {pin} set to {value} (device_address={self.device_address})"
        )

    def _handleRadio(self):
        length = self._getLength()

        if length == 0:
            LOGGER.warning(
                f"Empty SIM radio packet received (device_address={self.device_address})"
            )

        data = self.stdout.read(length)
        print("Handling radio ==========================================")
        # self._xbee.recieved_from_rocket(data)

    def _handleAnalogRead(self):
        length = self._getLength()
        assert length == 1
        pin = self.stdout.read(length)[0]
        print(f"Analog read request; pin = {pin}")
        # result = self._hw_sim.analog_read(pin).to_bytes(2, "big")
        # self._send_sim_packet(SimTxId.ANALOG_READ.value, result)

    def _handleSensorRead(self):
        length = self._getLength()
        assert length == 1
        sensor_id = self.stdout.read(length)[0]
        print(f"Sensor read request, id = {sensor_id}")
        # sensor_data = self._hw_sim.sensor_read(ID_TO_SENSOR[sensor_id])
        # endianness = ">" if self.bigEndianFloats else "<"
        # result = struct.pack(f"{endianness}{len(sensor_data)}f", *sensor_data)
        # self._send_sim_packet(SimTxId.SENSOR_READ.value, result)

    def _handleTimeUpdate(self):
        length = self._getLength()
        assert length == 4
        endianness = "big" if self.bigEndianInts else "little"
        delta_us = int.from_bytes(self.stdout.read(length), endianness)
        print(f"Handling time update, dt[us] = {delta_us}")
        # new_time_ms = self._hw_sim.time_update(delta_us)
        # self._send_sim_packet(
        #     SimTxId.TIME_UPDATE.value, new_time_ms.to_bytes(4, endianness)
        # )

    packetHandlers = {
        # DO NOT HANDLE "CONFIG" - it should be received only once at the start
        SimRxId.BUZZER.value: _handleBuzzer,
        SimRxId.DIGITAL_PIN_WRITE.value: _handleDigitalPinWrite,
        SimRxId.RADIO.value: _handleRadio,
        SimRxId.ANALOG_READ.value: _handleAnalogRead,
        SimRxId.SENSOR_READ.value: _handleSensorRead,
        SimRxId.TIME_UPDATE.value: _handleTimeUpdate,
    }

    def _run(self):
        LOGGER.debug(f"SIM connection started (device_address={self.device_address})")

        try:
            while True:
                id = self.stdout.read(1)[0]  # Returns 0 if process was killed

                if id not in self.packetHandlers.keys():
                    LOGGER.error(
                        f"SIM protocol violation!!! Shutting down. (device_address={self.device_address})"
                    )
                    for b in self.stdout.getHistory():
                        LOGGER.error(hex(b[0]))
                    LOGGER.error("^^^^ violation.")
                    return

                # Call packet handler
                self.packetHandlers[id](self)

        except Exception as ex:
            with self._shutdown_lock:
                if not self._is_shutting_down:
                    LOGGER.exception(
                        f"Error in SIM connection. (device_address={self.device_address})"
                    )

        LOGGER.warning(
            f"SIM connection thread shut down (device_address={self.device_address})"
        )

    def _getLength(self):
        [msb, lsb] = self.stdout.read(2)
        return (msb << 8) | lsb


class FirmwareNotFound(Exception):
    pass
