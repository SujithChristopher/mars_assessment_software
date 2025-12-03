# Module implementing the JEDI serial communication protocol that work with 
# the QT framework for emitting a signal when new data packets are available.
#
# Author: Sivakumar Balasubramanian
# Date: 24 July 2024
# Email: siva82kb@gmail.com


import struct
import serial
from serial import SerialException
import enum
import sys
import time
from PySide6.QtCore import (Signal, QThread)

_INDEBUG = False
_OUTDEBUG = False

class JediParsingStates(enum.Enum):
    LookingForHeader = 0
    FoundHeader1 = 1
    FoundHeader2 = 2
    ReadingPayload = 3
    CheckCheckSum = 4
    FoundFullPacket = 5


class JediComm(QThread):

    newdata_signal = Signal(list)

    def __init__(self, port: str | None = None, baudrate: int = 115200) -> None:
        super().__init__()
        self._port = port
        self._baudrate = baudrate
        self._ser = serial.Serial(port, baudrate)
        self._state = JediParsingStates.LookingForHeader
        self._in_payload = []
        self._out_payload = []

        # Payload reading variables.
        self._n = 0
        self._cnt = 0
        self._chksum = 0

        # thread related variables.
        self._abort = False
        self._pausing = False
        # self.setDaemon(False)
    
    @property
    def sleeping(self):
        """ Returns if the thread is sleeping.
        """
        return self._pausing
    
    def is_open(self):
        """Returns if the serial port is open.
        """
        return self._port if self._ser.is_open else ""

    def send_message(self, outbytes: list[int]):
        _outpayload = [0xAA, 0xAA, len(outbytes)+1, *outbytes]
        _outpayload.append(sum(_outpayload) % 256)
        # Send payload.
        if _OUTDEBUG:
            sys.stdout.write(f"\n [{time.time():6.3f}] [{len(_outpayload)}] Out data: ")
            for _elem in _outpayload:
                sys.stdout.write(f"{_elem} ")
        self._ser.write(bytearray(_outpayload))

    def run(self):
        """
        Thread operation.
        """
        self._state = JediParsingStates.LookingForHeader
        while self._ser.is_open and not self._abort:
            if self._pausing:
                self.msleep(100)
                continue
            self._read_handle_data()
            self.msleep(1)
        try:
            self._ser.close()  # safe to close here
        except:
            pass

    def pause(self):
        """
        Puts the current thread in a paused state.
        """
        # with self.state:
        self._pausing = True

    def wakeup(self):
        """
        Wake up a paused thread.
        """
        self._pausing = False

    def abort(self):
        """
        Aborts the current thread.
        """
        if self._pausing:
            self.wakeup()
        self._abort = True

    def _read_handle_data(self):
        """
        Reads and handles the received data by calling the inform function.
        """
        # Read full packets.
        if self._ser.in_waiting and _INDEBUG:
            # sys.stdout.write("\n New data: ")
            pass
        try:            
            while self._ser.in_waiting:
                bytes_available = self._ser.in_waiting
                if bytes_available > 0:
                    _waiting_bytes = self._ser.read(bytes_available)
                # _byte = self._ser.read()
                if _INDEBUG:
                    # print(_waiting_bytes)
                    pass
                for _byte in _waiting_bytes:
                    if  _INDEBUG:
                        # sys.stdout.write(f"{_byte} ")
                        pass
                    if self._state == JediParsingStates.LookingForHeader:
                        if _byte == 0xff:
                            self._state = JediParsingStates.FoundHeader1
                    elif self._state == JediParsingStates.FoundHeader1:
                        if _byte == 0xff:
                            self._state = JediParsingStates.FoundHeader2
                        else:
                            self._state = JediParsingStates.LookingForHeader
                    elif self._state == JediParsingStates.FoundHeader2:
                        # Payload size cannot be zero.
                        if _byte == 0:
                            self._state = JediParsingStates.LookingForHeader
                            continue
                        # Payload size is not zero.
                        self._n = _byte
                        self._cnt = 0
                        self._chksum = 255 + 255 + self._n
                        self._in_payload = [ 0 ] * (self._n - 1)
                        self._state = JediParsingStates.ReadingPayload
                    elif self._state == JediParsingStates.ReadingPayload:
                        self._in_payload[self._cnt] = _byte
                        self._chksum += _byte
                        self._cnt += 1
                        if self._cnt == self._n - 1:
                            self._state = JediParsingStates.CheckCheckSum
                    elif self._state == JediParsingStates.CheckCheckSum:
                        if self._chksum % 256 == _byte:
                            self._state = JediParsingStates.FoundFullPacket
                        else:
                            self._state = JediParsingStates.LookingForHeader
                    
                    # Handle full packet.
                    if self._state == JediParsingStates.FoundFullPacket:
                        if _INDEBUG:

                            
                            print('S ', len(self._in_payload),struct.unpack('>H', bytearray(self._in_payload[5:7])),self._in_payload[0], self._in_payload[1], self._in_payload[2], self._in_payload[3], self._in_payload[4],*struct.unpack('>H', bytearray(self._in_payload[2:4])), )
                            # print(struct.unpack('f', bytearray(self._in_payload[10:14])))
                            # print(struct.unpack('f', bytearray(self._in_payload[14:18])))
                            # print(struct.unpack('f', bytearray(self._in_payload[18:22])))
                            # print(struct.unpack('f', bytearray(self._in_payload[6:10])))
                            # print(struct.unpack('f', bytearray(self._in_payload[6:10])))
                            # print(struct.unpack('f', self._in_payload[:4]))
                            # print("Full packet received.")
                            pass
                            
                        self.newdata_signal.emit(self._in_payload)
                        self._state = JediParsingStates.LookingForHeader
        except SerialException:
            return


if __name__ == '__main__':
    jedireader = JediComm("COM4")
    jedireader.start()
    jedireader.send_message([0x05]) # Stop stream
    jedireader.send_message([0x04]) # Start stream
    jedireader.send_message([0x00])
    jedireader.send_message([0x08]) # diagnostics
    # jedireader.send_message([0x05]) # Stop stream

    # jedireader.send_message([0x08])
    # jedireader.send_message([0x80]) # diagnostics
    # jedireader.send_message([0x80])
    # jedireader.send_message([0x80])
    # jedireader.send_message([0x80])
    jedireader.send_message([0x80])
    jedireader.send_message([0x80])
    jedireader.send_message([0x80])
    jedireader.send_message([0x80])
    
    time.sleep(6)
    jedireader.send_message([0x80])

    jedireader.abort()