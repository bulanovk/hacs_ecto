from .base import EctoDevice

class EctoRelay8CH(EctoDevice):
    """8-канальное реле"""
    DEVICE_TYPE = 0xC1
    CHANNEL_COUNT = 8