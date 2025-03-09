#!/usr/bin/env python3
"""Pymodbus asynchronous Server Example.

An example of a multi threaded asynchronous server.

usage::

    server_async.py [-h] [--comm {tcp,udp,serial,tls}]
                    [--framer {ascii,rtu,socket,tls}]
                    [--log {critical,error,warning,info,debug}]
                    [--port PORT] [--store {sequential,sparse,factory,none}]
                    [--slaves SLAVES]

    -h, --help
        show this help message and exit
    -c, --comm {tcp,udp,serial,tls}
        set communication, default is tcp
    -f, --framer {ascii,rtu,socket,tls}
        set framer, default depends on --comm
    -l, --log {critical,error,warning,info,debug}
        set log level, default is info
    -p, --port PORT
        set port
        set serial device baud rate
    --store {sequential,sparse,factory,none}
        set datastore type
    --slaves SLAVES
        set number of slaves to respond to

The corresponding client can be started as:

    python3 client_sync.py

"""
import asyncio
import logging
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder
import sys
from collections.abc import Callable
from typing import Any


try:
    import helper  # type: ignore[import-not-found]
except ImportError:
    print("*** ERROR --> THIS EXAMPLE needs the example directory, please see \n\
          https://pymodbus.readthedocs.io/en/latest/source/examples.html\n\
          for more information.")
    sys.exit(-1)

from pymodbus import __version__ as pymodbus_version
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
    ModbusSparseDataBlock,
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import (
    StartAsyncSerialServer,
    StartAsyncTcpServer,
    StartAsyncTlsServer,
    StartAsyncUdpServer,
ModbusTcpServer
)



_logger = logging.getLogger(__file__)
_logger.setLevel(logging.INFO)


def setup_server(description=None, context=None, cmdline=None):
    """Run server setup."""
    args = helper.get_commandline(server=True, description=description, cmdline=cmdline)
    if context:
        args.context = context
    datablock: Callable[[], Any]
    if not args.context:
        _logger.info("### Create datastore")
        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
        builder.add_16bit_int(9999)
        datablock = lambda : ModbusSparseDataBlock({0x00: 0, 0x20: builder.to_registers()})  # pylint: disable=unnecessary-lambda-assignment
        context = {}
        context[8] = ModbusSlaveContext(
                    di=datablock(),
                    co=datablock(),
                    hr=datablock(),
                    ir=datablock(),
                )
        # Build data storage
        args.context = ModbusServerContext(slaves=context, single=False)

    # ----------------------------------------------------------------------- #
    # initialize the server information
    # ----------------------------------------------------------------------- #
    # If you don't set this or any fields, they are defaulted to empty strings.
    # ----------------------------------------------------------------------- #
    args.identity = ModbusDeviceIdentification(
        info_name={
            "VendorName": "Pymodbus",
            "ProductCode": "PM",
            "VendorUrl": "https://github.com/pymodbus-dev/pymodbus/",
            "ProductName": "Pymodbus Server",
            "ModelName": "Pymodbus Server",
            "MajorMinorRevision": pymodbus_version,
        }
    )
    return args


async def run_async_server(args) -> None:
    """Run server."""
    txt = f"### start ASYNC server, listening on {args.port} - {args.comm}"
    _logger.info(txt)
    await StartAsyncSerialServer(
            context=args.context,  # Data storage
            identity=args.identity,  # server identify
            # timeout=1,  # waiting time for request to complete
            port=args.port,  # serial port
            # custom_functions=[],  # allow custom handling
            framer=args.framer,  # The framer strategy to use
            stopbits=1,  # The number of stop bits to use
            bytesize=8,  # The bytesize of the serial messages
            parity="N",  # Which kind of parity to use
            baudrate=args.baudrate,  # The baud rate to use for the serial device
            # handle_local_echo=False,  # Handle local echo of the USB-to-RS485 adaptor
            ignore_missing_slaves=True,  # ignore request to a missing slave
            # broadcast_enable=False,  # treat slave 0 as broadcast address,
    )

async def async_helper() -> None:
    """Combine setup and run."""
    _logger.info("Starting...")
    run_args = setup_server(description="Run asynchronous server.")
    await run_async_server(run_args)


if __name__ == "__main__":
    asyncio.run(async_helper(), debug=True)