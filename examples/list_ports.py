#!/usr/bin/env python3

import re
from argparse import ArgumentParser, ArgumentTypeError

from alsa_midi import SequencerClient, SequencerPortType


def flag_parser(flag_type):
    prefix = flag_type.__name__ + "."
    prefix_l = len(prefix)

    def parse(string):
        result = flag_type(0)
        for value in re.split(r"[\s,;|]", string):
            if value.startswith(prefix):
                value = value[prefix_l:]
            try:
                result |= flag_type[value.upper()]
            except KeyError:
                raise ArgumentTypeError(f"Invalid {flag_type.__name__} value: {value!r}")
        return result

    return parse


def main():
    parser = ArgumentParser(description="List ALSA sequencer ports")
    parser.add_argument("--input", action="store_true",
                        help="Show input ports")
    parser.add_argument("--output", action="store_true",
                        help="Show output ports")
    parser.add_argument("--type", type=flag_parser(SequencerPortType),
                        default=SequencerPortType.MIDI_GENERIC,
                        help="Show only ports of this type (default: MIDI_GENERIC)")
    parser.add_argument("--system", action="store_true", default=False,
                        help="Include system ports")
    parser.add_argument("--no-midi-through", action="store_true", default=False,
                        help="Exclude 'Midi Through' ports")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show port details")

    args = parser.parse_args()

    client = SequencerClient("list_ports.py")

    ports = client.list_ports(input=args.input,
                              output=args.output,
                              type=args.type,
                              include_system=args.system,
                              include_midi_through=not args.no_midi_through)

    for port_info in ports:
        print(f"{port_info.client_id}:{port_info.port_id}"
              f" {port_info.client_name!r} {port_info.name!r}")
        if args.verbose:
            print(f"  capabilities    : {port_info.capability!s}")
            print(f"  type            : {port_info.type!s}")
            print(f"  midi channels   : {port_info.midi_channels}")
            print(f"  midi voices     : {port_info.midi_voices}")
            print(f"  synth voices    : {port_info.synth_voices}")
            print(f"  read subs.      : {port_info.read_use}")
            print(f"  write subs.     : {port_info.write_use}")
            print(f"  timestamping    : {port_info.timestamping}")
            print(f"  timestamp real  : {port_info.timestamp_real}")
            print(f"  timestamp queue : {port_info.timestamp_queue_id}")
            print()


if __name__ == '__main__':
    main()
