import typing
from sim_parser import SimReadParser

# def _grouper(iterable, n):
#     """
#     Iterate over iterable in groups (tuples) of n
#     """
#     args = [iter(iterable)] * n
#     return zip(*args)


# class ASCIIDecoder:
#     """
#     Readable binary file-like object.
#     """

#     def __init__(self, stream: typing.BinaryIO):
#         """
#         stream: any binary file-like object
#         """
#         self._stream = stream

#     def read(self, size: int):
#         raw = self._stream.read(size * 2)
#         if len(raw) == 0:
#             raise RuntimeError("Ran out of bytes to read")
#         elif len(raw) < size * 2:
#             raise RuntimeWarning(f"Read {len(raw)} bytes; expected {size*2}")

#         result = bytearray()
#         for msb, lsb in _grouper(raw, 2):
#             msb -= ord("A")
#             lsb -= ord("A")
#             result += (msb << 4 + lsb).to_bytes(1, "big")
#         return bytes(result)


with open("FW_SIM_log", "rb") as f:
    SimReadParser(f)
