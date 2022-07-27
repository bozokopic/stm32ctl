from pathlib import Path
import asyncio
import contextlib
import functools
import io
import logging.config
import sys

from hat import aio

from stm32ctl.args import (InfoArgs,
                           ReadArgs,
                           WriteArgs,
                           EraseArgs,
                           ExecuteArgs,
                           ProtectionArgs,
                           Args,
                           parse_args)
from stm32ctl.client import (Protection,
                             create_client)


def main():
    args = parse_args(sys.argv)

    if args.log:
        _set_logging(args.log)

    stdin, sys.stdin = sys.stdin.detach(), None
    stdout, sys.stdout = sys.stdout.detach(), None

    with contextlib.suppress(asyncio.CancelledError):
        aio.run_asyncio(async_main(args, stdin, stdout))


async def async_main(args: Args,
                     stdin: io.BufferedReader,
                     stdout: io.BufferedWriter):
    client = await create_client(port=args.port,
                                 baudrate=args.baudrate,
                                 skip_init=args.skip_init)

    try:
        for action_args in args.actions:
            if isinstance(action_args, InfoArgs):
                await _act_info(client, action_args, stdout)

            elif isinstance(action_args, ReadArgs):
                await _act_read(client, action_args, stdout, not args.log)

            elif isinstance(action_args, WriteArgs):
                await _act_write(client, action_args, stdin, not args.log)

            elif isinstance(action_args, EraseArgs):
                await _act_erase(client, action_args)

            elif isinstance(action_args, ExecuteArgs):
                await _act_execute(client, action_args)

            elif isinstance(action_args, ProtectionArgs):
                await _act_protection(client, action_args)

            else:
                raise ValueError('unsupported action')

    finally:
        await client.async_close()


def _set_logging(log_level):
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'formater': {
                'format': '[%(asctime)s %(levelname)s %(name)s] %(message)s'}},
        'handlers': {
            'handler': {
                'class': 'logging.StreamHandler',
                'formatter': 'formater',
                'level': log_level}},
        'root': {
            'level': log_level,
            'handlers': ['handler']},
        'disable_existing_loggers': False})


async def _act_info(client, args, stdout):
    info = await client.get_info()

    stdout.write(
        f'version: 0x{info.version:02x}\n'
        f'chip id: 0x{info.chip_id:04x}\n'
        f'device id: {info.device_id.hex(" ")}\n'
        f'flash size: {info.flash_size / 1024}K\n'.encode('utf-8'))
    stdout.flush()


async def _act_read(client, args, stdout, dynamic_progress):
    # TODO verify

    if args.progress and dynamic_progress:
        progress_cb = functools.partial(_print_progress, '\rreading:', '')

    elif args.progress:
        progress_cb = functools.partial(_print_progress, 'reading:', '\n')

    else:
        progress_cb = None

    data = await client.read(args.address, args.size, progress_cb)

    if args.progress and dynamic_progress:
        print(file=sys.stderr, flush=True)

    if args.path == Path('-'):
        stdout.write(data)
        stdout.flush()

    else:
        args.path.write_bytes(data)


async def _act_write(client, args, stdin, dynamic_progress):
    # TODO verify

    data = (stdin.read() if args.path == Path('-')
            else args.path.read_bytes())

    if args.progress and dynamic_progress:
        progress_cb = functools.partial(_print_progress, '\rwriting:', '')

    elif args.progress:
        progress_cb = functools.partial(_print_progress, 'writing:', '\n')

    else:
        progress_cb = None

    await client.write(args.address, data, progress_cb)

    if args.progress and dynamic_progress:
        print(file=sys.stderr, flush=True)


async def _act_erase(client, args):
    await client.erase(args.pages)


async def _act_execute(client, args):
    await client.execute(args.address)


async def _act_protection(client, args):
    if args.protect_read:
        await client.set_protection(Protection.PROTECT_READ)

    if args.unprotect_read:
        await client.set_protection(Protection.UNPROTECT_READ)

    if args.protect_write:
        await client.set_protection(Protection.PROTECT_WRITE)

    if args.unprotect_write:
        await client.set_protection(Protection.UNPROTECT_WRITE)


def _print_progress(msg, end, current, total):
    print(msg, f'{current}/{total} ({int(100 * current / total)}%)',
          end=end, file=sys.stderr, flush=True)


if __name__ == '__main__':
    sys.argv[0] = 'stm32ctl'
    sys.exit(main())
