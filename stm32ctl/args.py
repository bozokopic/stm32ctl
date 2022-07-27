from pathlib import Path
import getopt
import sys
import typing


class InfoArgs(typing.NamedTuple):
    pass


class ReadArgs(typing.NamedTuple):
    address: int = 0x0800_0000
    size: int = 64 * 1024
    path: Path = Path('-')
    progress: bool = False
    verify: bool = False


class WriteArgs(typing.NamedTuple):
    address: int = 0x0800_0000
    path: Path = Path('-')
    progress: bool = False
    verify: bool = False


class EraseArgs(typing.NamedTuple):
    pages: typing.Optional[typing.List[int]] = None


class ExecuteArgs(typing.NamedTuple):
    address: int = 0x0800_0000


class ProtectionArgs(typing.NamedTuple):
    protect_read: bool = False
    unprotect_read: bool = False
    protect_write: bool = False
    unprotect_write: bool = False


ActArgs = typing.Union[InfoArgs,
                       ReadArgs,
                       WriteArgs,
                       ExecuteArgs,
                       EraseArgs,
                       ProtectionArgs]


class Args(typing.NamedTuple):
    port: str = '/dev/ttyUSB0'
    baudrate: int = 115200
    skip_init: bool = False
    log: typing.Optional[str] = None
    actions: typing.List[ActArgs] = []


usage = r"""Usage:
  stm32ctl [<global_option>]... [<action> [<action_option>]...]...

STM32 system bootloader control

Actions:
  info               show device informations
  read               read binary data
  write              write binary data
  erase              erase flash memory
  execute            start application execution
  protection         change read/write protection

Global options:
  --help             show usage
  --port PORT        serial port (default /dev/ttyUSB0)
  --baudrate N       serial baudrate (default 115200)
  --skip-init        skip communication initialization
  --log {CRITICAL|ERROR|WARNING|INFO|DEBUG|NOTSET}
                     enable logging with provided minimal level

Read options:
  --address ADDR     starting address (default 0x0800_0000)
  --size N           number of bytes (default 64K)
  --path PATH        output file path or '-' for stdout (default '-')
  --progress         show progress
  --verify           verify read data

Write options:
  --address ADDR     starting address (default 0x0800_0000)
  --path PATH        input file path or '-' for stdin (default '-')
  --progress         show progress
  --verify           verify written data

Erase options:
  --pages {N|N1-N2},...
                     erase pages (or pages range) instead of all memory

Execute options:
  --address ADDR     starting address (default 0x0800_0000)

Protection options:
  --protect-read     protect read operations
  --unprotect-read   unprotect read operations
  --protect-write    protect write operations
  --unprotect-write  unprotect write operations
"""


def parse_args(argv: typing.List[str]
               ) -> Args:
    names = ['help', 'port=', 'baudrate=', 'skip-init', 'log=']

    try:
        result, rest = getopt.getopt(argv[1:], '', names)

    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print(usage, file=sys.stderr)
        sys.exit(1)

    args = Args(actions=[])
    for name, value in result:
        if name == '--help':
            print(usage, file=sys.stderr)
            sys.exit(1)

        elif name == '--port':
            args = args._replace(port=_parse_int(value))

        elif name == '--baudrate':
            args = args._replace(baudrate=_parse_int(value))

        elif name == '--skip-init':
            args = args._replace(skip_init=True)

        elif name == '--log':
            if value not in {'CRITICAL', 'ERROR', 'WARNING', 'INFO',
                             'DEBUG', 'NOTSET'}:
                print('invalid log level', file=sys.stderr)
                print(usage, file=sys.stderr)
                sys.exit(1)

            args = args._replace(log=value)

        else:
            raise ValueError('unsupported name')

    while rest:
        if rest[0] == 'info':
            info_args, rest = _parse_info_args(rest)
            args.actions.append(info_args)

        elif rest[0] == 'read':
            read_args, rest = _parse_read_args(rest)
            args.actions.append(read_args)

        elif rest[0] == 'write':
            write_args, rest = _parse_write_args(rest)
            args.actions.append(write_args)

        elif rest[0] == 'erase':
            erase_args, rest = _parse_erase_args(rest)
            args.actions.append(erase_args)

        elif rest[0] == 'execute':
            execute_args, rest = _parse_execute_args(rest)
            args.actions.append(execute_args)

        elif rest[0] == 'protection':
            protection_args, rest = _parse_protection_args(rest)
            args.actions.append(protection_args)

        else:
            print('unknown action', rest[0], file=sys.stderr)
            print(usage, file=sys.stderr)
            sys.exit(1)

    return args


def _parse_info_args(argv):
    names = ['help']

    try:
        result, rest = getopt.getopt(argv[1:], '', names)

    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print(usage, file=sys.stderr)
        sys.exit(1)

    args = InfoArgs()
    for name, value in result:
        if name == '--help':
            print(usage, file=sys.stderr)
            sys.exit(1)

        else:
            raise ValueError('unsupported name')

    return args, rest


def _parse_read_args(argv):
    names = ['help', 'address=', 'size=', 'path=', 'progress', 'verify']

    try:
        result, rest = getopt.getopt(argv[1:], '', names)

    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print(usage, file=sys.stderr)
        sys.exit(1)

    args = ReadArgs()
    for name, value in result:
        if name == '--help':
            print(usage, file=sys.stderr)
            sys.exit(1)

        elif name == '--address':
            args = args._replace(address=_parse_int(value))

        elif name == '--size':
            args = args._replace(size=_parse_int(value))

        elif name == '--path':
            args = args._replace(path=Path(value))

        elif name == '--progress':
            args = args._replace(progress=True)

        elif name == '--verify':
            args = args._replace(verify=True)

        else:
            raise ValueError('unsupported name')

    return args, rest


def _parse_write_args(argv):
    names = ['help', 'address=', 'path=', 'progress', 'verify']

    try:
        result, rest = getopt.getopt(argv[1:], '', names)

    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print(usage, file=sys.stderr)
        sys.exit(1)

    args = WriteArgs()
    for name, value in result:
        if name == '--help':
            print(usage, file=sys.stderr)
            sys.exit(1)

        elif name == '--address':
            args = args._replace(address=_parse_int(value))

        elif name == '--path':
            args = args._replace(path=Path(value))

        elif name == '--progress':
            args = args._replace(progress=True)

        elif name == '--verify':
            args = args._replace(verify=True)

        else:
            raise ValueError('unsupported name')

    return args, rest


def _parse_erase_args(argv):
    names = ['help', 'pages=']

    try:
        result, rest = getopt.getopt(argv[1:], '', names)

    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print(usage, file=sys.stderr)
        sys.exit(1)

    args = EraseArgs()
    for name, value in result:
        if name == '--help':
            print(usage, file=sys.stderr)
            sys.exit(1)

        elif name == '--pages':
            args = args._replace(pages=sorted(_parse_pages(value)))

        else:
            raise ValueError('unsupported name')

    return args, rest


def _parse_execute_args(argv):
    names = ['help', 'address=']

    try:
        result, rest = getopt.getopt(argv[1:], '', names)

    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print(usage, file=sys.stderr)
        sys.exit(1)

    args = ExecuteArgs()
    for name, value in result:
        if name == '--help':
            print(usage, file=sys.stderr)
            sys.exit(1)

        elif name == '--address':
            args = args._replace(address=_parse_int(value))

        else:
            raise ValueError('unsupported name')

    return args, rest


def _parse_protection_args(argv):
    names = ['help', 'protect-read', 'unprotect-read', 'protect-write',
             'unprotect-write']

    try:
        result, rest = getopt.getopt(argv[1:], '', names)

    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print(usage, file=sys.stderr)
        sys.exit(1)

    args = ProtectionArgs()
    for name, value in result:
        if name == '--help':
            print(usage, file=sys.stderr)
            sys.exit(1)

        elif name == '--protect-read':
            args = args._replace(protect_read=True)

        elif name == '--unprotect-read':
            args = args._replace(unprotect_read=True)

        elif name == '--protect-write':
            args = args._replace(protect_write=True)

        elif name == '--unprotect-write':
            args = args._replace(unprotect_write=True)

        else:
            raise ValueError('unsupported name')

    return args, rest


def _parse_int(x):
    if x.endswith('K'):
        return _parse_int(x[:-1]) * 1024

    if x.startswith('0x'):
        return int(x, base=16)

    return int(x)


def _parse_pages(value):
    for segment in value.split(','):
        if not segment:
            continue

        if '-' not in segment:
            yield int(segment)
            continue

        start_str, stop_str = segment.split('-', 1)
        start, stop = int(start_str), int(stop_str)
        yield from range(start, stop + 1)
