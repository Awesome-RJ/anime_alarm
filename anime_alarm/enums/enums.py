from enum import Enum, IntEnum


class Resolution(Enum):
    """
    This represents different resolution configs
    """
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    ULTRA = 'ultra'


# map resolution enums to resolution values
resolutions = {
        Resolution.LOW: '360P',
        Resolution.MEDIUM: '480P',
        Resolution.HIGH: '720P',
        Resolution.ULTRA: '1080P'
    }
