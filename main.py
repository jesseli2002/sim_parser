import typing
from sim_parser import SimReadParser

with open("FW_SIM_log", "rb") as f:
    SimReadParser(f)
