"""Asciicast v2 record formats

Full specification: https://github.com/asciinema/asciinema/blob/develop/doc/asciicast-v2.md
"""
import abc
import codecs
import json
from collections import namedtuple

utf8_decoder = codecs.getincrementaldecoder('utf-8')('replace')


class AsciiCastRecord(abc.ABC):
    """Generic Asciicast v2 record format"""
    @abc.abstractmethod
    def to_json_line(self):
        raise NotImplementedError

    @classmethod
    def from_json_line(cls, line):
        if type(json.loads(line)) == dict:
            return AsciiCastHeader.from_json_line(line)
        elif type(json.loads(line)) == list:
            return AsciiCastEvent.from_json_line(line)
        else:
            raise NotImplementedError


_AsciiCastHeader = namedtuple('AsciiCastHeader', ['version', 'width', 'height', 'theme'])


AsciiCastTheme = namedtuple('AsciiCastTheme', ['fg', 'bg', 'palette'])
AsciiCastTheme.__doc__ = """Color theme of the terminal. All colors must use the '#rrggbb' format"""
AsciiCastTheme.fg.__doc__ = """Default text color"""
AsciiCastTheme.bg.__doc__ = """Default background color"""
AsciiCastTheme.palette.__doc__ = """Colon separated list of the 8 or 16 terminal colors"""


class AsciiCastHeader(AsciiCastRecord, _AsciiCastHeader):
    """Header record

    version: Version of the asciicast file format
    width: Initial number of columns of the terminal
    height: Initial number of lines of the terminal
    theme: Color theme of the terminal
    """
    types = {
        'version': {int},
        'width': {int},
        'height': {int},
        'theme': {type(None), AsciiCastTheme},
    }

    def __new__(cls, version, width, height, theme):
        self = super(AsciiCastHeader, cls).__new__(cls, version, width, height, theme)
        for attr in AsciiCastHeader._fields:
            type_attr = type(self.__getattribute__(attr))
            if type_attr not in cls.types[attr]:
                raise TypeError('Invalid type for attribute {}: {} '.format(attr, type_attr) +
                                '(possible type: {})'.format(cls.types[attr]))

        if version != 2:
            raise ValueError('Only asciicast v2 format is supported')
        return self

    def to_json_line(self):
        attributes = self._asdict()
        if self.theme is not None:
            attributes['theme'] = self.theme._asdict()
        else:
            del attributes['theme']

        return json.dumps(attributes, ensure_ascii=False)

    @classmethod
    def from_json_line(cls, line):
        attributes = json.loads(line)
        filtered_attributes = {attr: attributes[attr] if attr in attributes else None
                               for attr in AsciiCastHeader._fields}
        if filtered_attributes['theme'] is not None:
            filtered_attributes['theme'] = AsciiCastTheme(**filtered_attributes['theme'])
        return cls(**filtered_attributes)


_AsciiCastEvent = namedtuple('AsciiCastEvent', ['time', 'event_type', 'event_data', 'duration'])


class AsciiCastEvent(AsciiCastRecord, _AsciiCastEvent):
    """Event record

    time: Time elapsed since the beginning of the recording in seconds
    event_type: Type 'o' if the data was captured on the standard output of the terminal, type
                'i' if it was captured on the standard input
    event_data: Data captured during the recording
    duration: Duration of the event in seconds (non standard field)
    """
    types = {
        'time': {int, float},
        'event_type': {str},
        'event_data': {bytes},
        'duration': {type(None), int, float},
    }

    def __new__(cls, *args, **kwargs):
        self = super(AsciiCastEvent, cls).__new__(cls, *args, **kwargs)
        for attr in AsciiCastEvent._fields:
            type_attr = type(self.__getattribute__(attr))
            if type_attr not in cls.types[attr]:
                raise TypeError('Invalid type for attribute {}: {} '.format(attr, type_attr) +
                                '(possible type: {})'.format(cls.types[attr]))
        return self

    def to_json_line(self):
        event_data = utf8_decoder.decode(self.event_data)
        attributes = [self.time, self.event_type, event_data]
        return json.dumps(attributes, ensure_ascii=False)

    @classmethod
    def from_json_line(cls, line):
        attributes = json.loads(line)
        time, event_type, event_data = attributes
        event_data = event_data.encode('utf-8')
        return cls(time, event_type, event_data, None)
