"""Classes for communicating with the Storm Audio ISP series sound processors"""

from __future__ import annotations
from decimal import *
from enum import IntFlag, auto

import typing

import telnetlib3

from .constants import *
from .line_reader import *


class DeviceState:
    def __init__(
        self
    ):
        self.brand: str = None
        self.model: str = None
        self.power_command: PowerCommand = None
        self.processor_state: ProcessorState = None
        self.inputs: list(Input) = None
        self.input: int = None
        self.input_zone2: int = None


class Input:
    def __init__(
        self,
        name: str,
        id: int,
        video_in_id: VideoInputID,
        audio_in_id: AudioInputID,
        audio_zone2_in_id: AudioZone2InputID,
        delay_ms: Decimal
    ):
        self.name: str = name
        self.id: int = id
        self.video_in_id: VideoInputID = video_in_id
        self.audio_in_id: AudioInputID = audio_in_id
        self.audio_zone2_in_id: AudioZone2InputID = audio_zone2_in_id
        self.delay_ms: Decimal = delay_ms


class ReadLinesResult(IntFlag):
    NONE = 0
    COMPLETE = auto()
    INCOMPLETE = auto()
    IGNORED = auto()


class TelnetClient():
    """Represents a client for communicating with the telnet server of an
        Storm Audio ISP sound processor."""

    def __init__(
        self,
        host
    ):
        self._device_state: DeviceState = DeviceState()
        self._reader = None
        self._writer = None
        self._host: str = host
        self._remaining_output: str = None
        self._read_lines: TokenizedLinesReader = None

    def get_device_state(
        self
    ) -> DeviceState:
        return self._device_state

    async def async_connect(
        self
    ) -> None:
        """Connects to the telnet server and reads data on the async
        event loop."""
        self._read_lines = TokenizedLinesReader()
        self._remaining_output = ''

        self._reader, self._writer = await telnetlib3.open_connection(
            self._host,
            connect_minwait=0.0,
            connect_maxwait=0.0,
            shell=self._read_loop
        )

    def disconnect(
        self
    ) -> None:
        """Disconnects from the telnet server."""
        self._writer.close()

    async def _read_loop(
        self,
        reader,
        writer
    ) -> None:
        """Async loop to read data received from the telnet server;
        sets device state as a result of data received."""

        while True:
            read_output = await reader.read(1024)
            if not read_output:
                # EOF
                break

            # Append new read output to any prior remaining output
            output = self._remaining_output + read_output

            # Parse the complete lines from the output
            output_lines = output.split('\n')

            # Add all complete lines to the read lines; excludes final
            # index, which is partial output (no CR yet)
            line_count = len(output_lines)
            if (line_count > 1):
                for line in output_lines:
                    print(line)
                self._read_lines.add_lines(output_lines[0: line_count - 1])

            # Save the remaining partial output
            self._remaining_output = output_lines[len(output_lines) - 1]

            while self._read_lines.has_next_line():
                read_result: ReadLinesResult = ReadLinesResult.NONE

                read_result |= self._eval__single_bracket_field(
                    ['ssp', 'brand'],
                    lambda x: self._device_state.__setattr__('brand', x),
                    lambda x: x.strip('"')
                )
                read_result |= self._eval__single_bracket_field(
                    ['ssp', 'model'],
                    lambda x: self._device_state.__setattr__('model', x),
                    lambda x: x.strip('"')
                )
                read_result |= self._eval__line(
                    ['ssp', 'power'],
                    self._eval_power_command
                )
                read_result |= self._eval__line(
                    ['ssp', 'procstate'],
                    self._eval_processor_state
                )
                read_result |= self._eval__line(
                    ['ssp', 'input', 'start'],
                    self._eval_inputs
                )
                read_result |= self._eval__single_bracket_field(
                    ['ssp', 'input'],
                    lambda x: self._device_state.__setattr__('input', x),
                    lambda x: int(x)
                )
                read_result |= self._eval__single_bracket_field(
                    ['ssp', 'inputZone2'],
                    lambda x: self._device_state.__setattr__('input_zone2', x),
                    lambda x: int(x)
                )

                if read_result & ReadLinesResult.INCOMPLETE:
                    # At least one line evaluator didn't have enough lines.
                    break

                if read_result == ReadLinesResult.IGNORED:
                    # All evaluators ignored the line; remove it.
                    self._read_lines.read_next_line()
                    self._read_lines.consume_read_lines()

    async def _async_send_command(
        self,
        command: str
    ) -> None:
        """Sends given command to the server. Automatically appends
            CR to the command string."""
        self._writer.write(command + '\n')
        await self._writer.drain()

    def _eval__line(
        self,
        expected_tokens: list(str),
        continue_fn,
    ) -> ReadLinesResult:
        if self._read_lines.has_next_line():
            line: TokenizedLineReader = self._read_lines.read_next_line()
            if line.pop_next_tokens_if_equal(expected=expected_tokens):
                read_result: ReadLinesResult = continue_fn(line)
                if read_result == ReadLinesResult.COMPLETE:
                    self._read_lines.consume_read_lines()
                else:
                    self._read_lines.reset_read_lines()
                return read_result
            self._read_lines.reset_read_lines()
            return ReadLinesResult.IGNORED
        return ReadLinesResult.INCOMPLETE

    def _eval__single_bracket_field(
        self,
        expected_tokens: list(str),
        set_fn,
        convert_fn
    ) -> ReadLinesResult:
        def parse_bracket_field(line: TokenizedLineReader):
            bracket_fields: list(str) = line.pop_next_token()
            if type(bracket_fields) is list:
                set_fn(convert_fn(bracket_fields[0]))
                return ReadLinesResult.COMPLETE
            return ReadLinesResult.IGNORED

        return self._eval__line(
            expected_tokens=expected_tokens,
            continue_fn=parse_bracket_field
        )

    def _eval_power_command(
        self,
        line: TokenizedLineReader
    ) -> ReadLinesResult:
        if line.pop_next_token_if_equal('on'):
            self._device_state.power_command = PowerCommand.ON
        elif line.pop_next_token_if_equal('off'):
            self._device_state.power_command = PowerCommand.OFF
        else:
            return ReadLinesResult.IGNORED
        return ReadLinesResult.COMPLETE

    def _eval_processor_state(
        self,
        line: TokenizedLineReader
    ) -> ReadLinesResult:
        bracket_fields: list(str) = line.pop_next_token()
        if type(bracket_fields) is list:
            if bracket_fields[0] == '0':
                self._device_state.processor_state = ProcessorState.OFF
            elif bracket_fields[0] == '1':
                self._device_state.processor_state = ProcessorState.INITIALIZING \
                    if self._device_state.power_command == PowerCommand.ON \
                    else ProcessorState.SHUTTING_DOWN
            elif bracket_fields[0] == '2':
                self._device_state.processor_state = ProcessorState.ON
            else:
                return ReadLinesResult.IGNORED
            return ReadLinesResult.COMPLETE
        return ReadLinesResult.IGNORED

    def _eval_inputs(
        self,
        line: TokenizedLineReader
    ) -> ReadLinesResult:
        new_inputs: list(Input) = []
        while self._read_lines.has_next_line():
            line = self._read_lines.read_next_line()
            if line.pop_next_tokens_if_equal(['ssp', 'input', 'list']):
                bracket_fields: list(str) = line.pop_next_token()
                if type(bracket_fields) is list:
                    input = Input(
                        name=bracket_fields[0].strip('"'),
                        id=int(bracket_fields[1]),
                        video_in_id=VideoInputID(
                            int(bracket_fields[2])),
                        audio_in_id=AudioInputID(
                            int(bracket_fields[3])),
                        audio_zone2_in_id=AudioZone2InputID(
                            int(bracket_fields[4])),
                        delay_ms=Decimal(bracket_fields[6])
                    )
                    new_inputs.append(input)
                else:
                    return ReadLinesResult.IGNORED
            elif line.pop_next_tokens_if_equal(['ssp', 'input', 'end']):
                # set input list
                self._device_state.inputs = new_inputs
                return ReadLinesResult.COMPLETE
            else:
                return ReadLinesResult.IGNORED
        return ReadLinesResult.INCOMPLETE
