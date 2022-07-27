import collections
import itertools
import struct
import typing
import enum

from hat import aio

from stm32ctl.connection import (CmdType,
                                 connect)


ProgressCb = typing.Callable[[int, int], None]


class Protection(enum.Enum):
    PROTECT_READ = 0
    UNPROTECT_READ = 1
    PROTECT_WRITE = 2
    UNPROTECT_WRITE = 3


class Info(typing.NamedTuple):
    version: int
    chip_id: int
    device_id: bytes
    flash_size: int


async def create_client(port: str,
                        baudrate: int,
                        skip_init: bool
                        ) -> 'Client':
    client = Client()
    client._conn = await connect(port=port,
                                 baudrate=baudrate,
                                 skip_init=skip_init)

    try:
        res = await client._conn.get_commands()
        client._version = res.version
        client._cmd_types = res.cmd_types

    except Exception:
        await aio.uncancellable(client.async_close())
        raise

    return client


class Client(aio.Resource):

    @property
    def async_group(self):
        return self._conn.async_group

    async def get_info(self) -> Info:
        if CmdType.GET_CHIP_ID not in self._cmd_types:
            raise Exception('get chip id not supported')

        if CmdType.READ not in self._cmd_types:
            raise Exception('read not supported')

        chip_id = await self._conn.get_chip_id()
        device_id = await self._conn.read(0x1FFF_F7E8, 12)
        flash_size_bytes = await self._conn.read(0x1FFF_F7E0, 2)

        flash_size = struct.unpack('<H', flash_size_bytes)[0] * 1024

        return Info(version=self._version,
                    chip_id=chip_id,
                    device_id=device_id,
                    flash_size=flash_size)

    async def set_protection(self, protection: Protection):
        if protection == Protection.PROTECT_READ:
            if CmdType.PROTECT_READ not in self._cmd_types:
                raise Exception('protect read not supported')

            await self._conn.protect_read()

        elif protection == Protection.UNPROTECT_READ:
            if CmdType.UNPROTECT_READ not in self._cmd_types:
                raise Exception('unprotect read not supported')

            await self._conn.unprotect_read()

        elif protection == Protection.PROTECT_WRITE:
            if CmdType.PROTECT_WRITE not in self._cmd_types:
                raise Exception('protect write not supported')

            await self._conn.protect_write()

        elif protection == Protection.UNPROTECT_WRITE:
            if CmdType.UNPROTECT_WRITE not in self._cmd_types:
                raise Exception('unprotect write not supported')

            await self._conn.unprotect_write()

        else:
            raise ValueError('unsupported protection')

    async def read(self,
                   start_address: int,
                   size: int,
                   progress_cb: typing.Optional[ProgressCb] = None
                   ) -> bytes:
        if CmdType.READ not in self._cmd_types:
            raise Exception('read not supported')

        if progress_cb:
            total_size = size
            read_size = 0
            progress_cb(read_size, total_size)

        segments = collections.deque()
        while size > 0:
            segment_size = min(size, 0x100)
            segment = await self._conn.read(start_address, segment_size)

            segments.append(segment)
            start_address += segment_size
            size -= segment_size

            if progress_cb:
                read_size += segment_size
                progress_cb(read_size, total_size)

        return bytes(itertools.chain.from_iterable(segments))

    async def write(self,
                    start_address: int,
                    data: bytes,
                    progress_cb: typing.Optional[ProgressCb] = None):
        if CmdType.WRITE not in self._cmd_types:
            raise Exception('write not supported')

        if progress_cb:
            total_size = len(data)
            written_size = 0
            progress_cb(written_size, total_size)

        data = memoryview(data)
        while data:
            segment_size = min(len(data), 0x100)
            await self._conn.write(start_address, data[:segment_size])

            data = data[segment_size:]
            start_address += segment_size

            if progress_cb:
                written_size += segment_size
                progress_cb(written_size, total_size)

    async def erase(self, pages: typing.Optional[typing.List[int]] = None):
        if CmdType.ERASE not in self._cmd_types:
            raise Exception('erase not supported')

        await self._conn.erase(pages)

    async def execute(self, start_address: int):
        if CmdType.EXECUTE not in self._cmd_types:
            raise Exception('execute not supported')

        await self._conn.execute(start_address)
