import enum
import typing
import struct
import itertools
import logging

from hat import aio
from hat.drivers import serial


mlog = logging.getLogger(__name__)


class CmdType(enum.Enum):
    GET_COMMANDS = 0x00
    GET_PROTECTION = 0x01
    GET_CHIP_ID = 0x02
    READ = 0x11
    EXECUTE = 0x21
    WRITE = 0x31
    ERASE = 0x43
    ERASE_EXTENDED = 0x44
    SPECIAL = 0x50
    SPECIAL_EXTENDED = 0x51
    PROTECT_READ = 0x82
    UNPROTECT_READ = 0x92
    PROTECT_WRITE = 0x63
    UNPROTECT_WRITE = 0x73
    CHECK_CRC = 0xA1


class CommandsRes(typing.NamedTuple):
    version: int
    cmd_types: typing.Set[CmdType]


class ProtectionRes(typing.NamedTuple):
    version: int
    status: int
    counter: int


async def connect(port: str,
                  baudrate: int,
                  skip_init: bool
                  ) -> 'Connection':
    conn = Connection()

    mlog.debug('opening serial endpoint on %s', port)
    conn._conn = await serial.create(port,
                                     baudrate=baudrate,
                                     parity=serial.Parity.EVEN)

    if skip_init:
        return conn

    try:
        mlog.debug('sending initial byte')
        await conn._conn.write(b'\x7F')
        await conn._receive_ack()

    except Exception:
        await aio.uncancellable(conn.async_close())
        raise

    return conn


class Connection(aio.Resource):

    @property
    def async_group(self):
        return self._conn.async_group

    async def get_commands(self) -> CommandsRes:
        mlog.debug('sending get commands command')
        await self._send([CmdType.GET_COMMANDS.value])

        count_bytes = await self._conn.read(1)
        count = count_bytes[0]

        version_bytes = await self._conn.read(1)
        version = version_bytes[0]
        mlog.debug('received version %s', version)

        cmd_types_bytes = await self._conn.read(count)
        cmd_types = {CmdType(i) for i in cmd_types_bytes}

        if mlog.isEnabledFor(logging.DEBUG):
            mlog.debug('received supported commands (%s)',
                       ', '.join(hex(i.value) for i in cmd_types))

        await self._receive_ack()

        return CommandsRes(version, cmd_types)

    async def get_protection(self) -> ProtectionRes:
        mlog.debug('sending get protection command')
        await self._send([CmdType.GET_PROTECTION.value])

        version_bytes = await self._conn.read(1)
        version = version_bytes[0]
        mlog.debug('received version %s', version)

        protection_bytes = await self._conn.read(2)
        status, counter = protection_bytes
        mlog.debug('received status %s and counter %s', status, counter)

        await self._receive_ack()

        return ProtectionRes(version, status, counter)

    async def get_chip_id(self) -> int:
        mlog.debug('sending get chip id command')
        await self._send([CmdType.GET_CHIP_ID.value])

        count_bytes = await self._conn.read(1)
        count = count_bytes[0]

        chip_id_bytes = await self._conn.read(count + 1)
        chip_id = int.from_bytes(chip_id_bytes, byteorder='big')
        mlog.debug('received chip id %s', chip_id)

        await self._receive_ack()

        return chip_id

    async def read(self,
                   start_address: int,
                   size: int
                   ) -> bytes:
        if size > 0x100:
            raise ValueError('unsupported size')

        mlog.debug('sending read command')
        await self._send([CmdType.READ.value])

        mlog.debug('sending start address %s', start_address)
        start_address_bytes = struct.pack('>I', start_address)
        await self._send(start_address_bytes)

        mlog.debug('sending size %s', size)
        await self._send([size - 1])

        data = await self._conn.read(size)

        return data

    async def write(self,
                    start_address: int,
                    data: bytes):
        size = len(data)
        if size > 0x100 or size < 1:
            raise ValueError('unsupported data')

        mlog.debug('sending write command')
        await self._send([CmdType.WRITE.value])

        mlog.debug('sending start address %s', start_address)
        start_address_bytes = struct.pack('>I', start_address)
        await self._send(start_address_bytes)

        mlog.debug('sending write data (length %s)', len(data))
        await self._send(itertools.chain([size - 1], data))

    async def execute(self, start_address: int):
        mlog.debug('sending execute command')
        await self._send([CmdType.EXECUTE.value])

        mlog.debug('sending start address %s', start_address)
        start_address_bytes = struct.pack('>I', start_address)
        await self._send(start_address_bytes)

    async def erase(self, pages: typing.Optional[typing.List[int]] = None):
        if pages is not None:
            size = len(pages)
            if size < 1 or size > 0xFF:
                raise ValueError('unsupported pages length')

        mlog.debug('sending erase command')
        await self._send([CmdType.ERASE.value])

        if pages is None:
            mlog.debug('sending erase all pages')
            await self._send([0xFF])
            return

        if mlog.isEnabledFor(logging.DEBUG):
            log_data = (f'count {size}' if size > 10
                        else f'pages {", ".join(str(page) for page in pages)}')
            mlog.debug('sending erase pages (%s)', log_data)

        await self._send(itertools.chain([size - 1], pages))

    async def erase_extended(self):
        raise NotImplementedError()

    async def protect_read(self):
        mlog.debug('sending protect read command')
        await self._send([CmdType.PROTECT_READ.value])

        await self._receive_ack()

    async def unprotect_read(self):
        mlog.debug('sending unprotect read command')
        await self._send([CmdType.UNPROTECT_READ.value])

        await self._receive_ack()

    async def protect_write(self):
        raise NotImplementedError()

    async def unprotect_write(self):
        mlog.debug('sending unprotect write command')
        await self._send([CmdType.UNPROTECT_WRITE.value])

        await self._receive_ack()

    async def special(self):
        raise NotImplementedError()

    async def special_extended(self):
        raise NotImplementedError()

    async def check_crc(self) -> int:
        raise NotImplementedError()

    async def _send(self, data):
        data_with_checksum = bytes(_get_data_with_checksum(data))

        if mlog.isEnabledFor(logging.DEBUG):
            size = len(data_with_checksum)
            log_data = (f'length {size}' if size > 10
                        else data_with_checksum.hex(' '))
            mlog.debug('sending data with checksum (%s)', log_data)

        await self._conn.write(data_with_checksum)

        await self._receive_ack()

    async def _receive_ack(self):
        mlog.debug('waiting for ACK')
        res = await self._conn.read(1)

        if res == b'\x1f':
            raise Exception('received NACK')

        if res != b'\x79':
            raise Exception(f'received unknown response: 0x{res[0]:02x}')

        mlog.debug('received ACK')


def _get_data_with_checksum(data):
    count = 0
    crc = 0

    for i in data:
        crc = 0xFF & (crc ^ i)
        count += 1
        yield i

    if count < 1:
        raise ValueError('invalid data size')

    if count < 2:
        crc = 0xFF & ~crc

    yield crc
