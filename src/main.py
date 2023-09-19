"""hi"""

import asyncio
from decimal import Decimal
import signal

from stormaudio_isp_telnet.telnet_client import (
    TelnetClient
)

from stormaudio_isp_telnet.constants import PowerCommand


# def db_to_percentage(db: Decimal) -> Decimal:
#     decimalDb: Decimal = Decimal(db)
#     return (Decimal(10) ** (decimalDb / Decimal(10))) * Decimal(100)


# def percentage_to_db(percentage: Decimal) -> Decimal:
#     decimalPercentage: Decimal = Decimal(percentage)
#     return (decimalPercentage / Decimal(100)).log10() * Decimal(10)

ZERO = Decimal(0)
ONE = Decimal(1)
ONE_HUNDRED = Decimal(100)

volume_control_decibel_range: Decimal = Decimal(60)
log_a: Decimal = Decimal(1) / \
    (Decimal(10) ** (volume_control_decibel_range / Decimal(20)))
log_b: Decimal = (Decimal(1) / Decimal(log_a)).ln()


def volume_level_to_decibels(volume_level: Decimal) -> Decimal:
    if volume_level <= ZERO:
        return ONE_HUNDRED
    elif volume_level >= ONE:
        return ZERO
    x = log_a * (log_b * volume_level).exp()
    return Decimal(20) * x.log10()


def decibels_to_volume_level(decibels: Decimal) -> Decimal:
    if decibels <= -volume_control_decibel_range:
        return ZERO
    elif decibels >= ZERO:
        return ONE
    x = 10 ** (decibels / Decimal(20))
    return (x / log_a).ln() / log_b


async def _async_on_device_state_updated():
    print('Device state updated')


async def _async_on_disconnected():
    print('Disconnected')


async def _async_on_raw_line_received(line: str):
    print(line)


class Interrupted():
    def __init__(self):
        self.set: bool = False


async def do_it():
    """xxx"""
    # client = TelnetClient(
    #     '10.111',
    #     async_on_device_state_updated=_async_on_device_state_updated,
    #     async_on_disconnected=_async_on_disconnected,
    #     async_on_raw_line_received=_async_on_raw_line_received
    # )
    # try:
    #     await client.async_connect()
    # except ConnectionError:
    #     print('Connection error')

    # db29 = decibels_to_volume_level(-29)
    # db52 = decibels_to_volume_level(-30)
    # hi51 = volume_level_to_decibels(Decimal(0.51))
    # hi52 = volume_level_to_decibels(Decimal(0.52))
    # hi53 = volume_level_to_decibels(Decimal(0.53))

    client = TelnetClient(
        '10.111.16.60',
        async_on_device_state_updated=_async_on_device_state_updated,
        async_on_disconnected=_async_on_disconnected,
        async_on_raw_line_received=_async_on_raw_line_received
    )
    await client.async_connect()

    interrupted: Interrupted = Interrupted()

    def interrupt_handler(signum, frame):
        interrupted.set = True
    signal.signal(signal.SIGINT, interrupt_handler)

    # await asyncio.sleep(2)

    # await client.async_set_power_command(power_command=PowerCommand.OFF)
    await client.async_set_power_command(power_command=PowerCommand.ON)

    # await client.async_set_input_id(1)
    # await client.async_set_input_id(11)

    # await client.async_set_input_zone2_id(11)
    # await client.async_set_input_zone2_id(0)

    # await client.async_set_mute(True)
    # await client.async_set_mute(False)

    # await client.async_set_volume(-100)
    # await client.async_set_volume(Decimal(-97.8))
    # await client.async_set_volume(-50)

    # await client.async_set_preset_id(5)
    # await client.async_set_preset_id(6)
    # await client.async_set_preset_id(7)

    while not interrupted.set:
        await asyncio.sleep(0)

    print('Disconnecting...')
    await client.async_disconnect()

    # result = await client.async_get_power_status()
    # print(result)

    # command_result = await client.async_map_input_to_output(
    #     InputID.create_digital('a'),
    #     OutputID.create_digital('a')
    # )
    # print(command_result)

    # all_inputs = InputID.all()
    # for i in all_inputs:
    #     print(i.name)

    # all_outputs = OutputID.all()
    # for i in all_outputs:
    #     print(i.name)

    # _available_inputs = InputID.all()
    # _input_id_to_name = dict(
    #     map(lambda i: (str(i), i.name), _available_inputs)
    # )
    # _input_name_to_id = {v: k for k, v in _input_id_to_name.items()}

    # print(_input_id_to_name)
    # print(_input_name_to_id)

    # await client.async_set_output_power_state(OutputID.create_analog(1), False)
    # await client.async_set_output_power_state(OutputID.create_analog(1), True)
    # await client.async_set_output_volume(OutputID.create_analog(1), 85)

    # raw_status = await client.async_get_system_status_raw()
    # print(raw_status)

    # sys_status = await client.async_get_system_status()
    # print(sys_status.name)
    # for output_key in enumerate(sys_status.outputs):
    #     output = sys_status.outputs[output_key[1]]
    #     print(output.output_id + " " + output.name +
    #           " " + output.input_id + " " + str(output.volume))

    # client.disconnect()

asyncio.run(do_it())
