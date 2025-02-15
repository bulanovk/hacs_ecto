from .base import EctoDevice

class EctoCH10BinarySensor(EctoDevice):
    """10-канальный бинарный датчик"""
    DEVICE_TYPE = 0x59
    CHANNEL_COUNT = 10