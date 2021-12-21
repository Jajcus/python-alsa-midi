#!/usr/bin/env python3

from argparse import ArgumentParser

from alsa_midi import WRITE_PORT, Address, SequencerClient


def main():
    parser = ArgumentParser(description="Dump / sniff ALSA sequencer events")
    parser.add_argument("--port", "-p", type=Address, action="append",
                        help="Connect to the specific port")

    args = parser.parse_args()

    client = SequencerClient("dump_events.py")
    port = client.create_port("input", WRITE_PORT)
    addr = Address(port)

    print(f"Listening for events at sequecncer port {addr}")

    if args.port:
        for target_port in args.port:
            port.connect_from(target_port)

    try:
        while True:
            event = client.event_input()
            print(repr(event))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
