import typing
from sim_parser import SimReadParser

FILES = [
    "FW_SIM_log",
    "test-accelerometer-deadlock-1.txt",
    "test-baro-altitude-deadlock-1.txt",
    "test-baro-altitude-deadlock-2.txt",
    "test-imu-deadlock-1.txt",
]

with open(FILES[1], "rb") as f:
    SimReadParser(f)
