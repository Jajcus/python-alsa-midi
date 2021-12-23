#!/usr/bin/env python3

import time
from argparse import ArgumentParser

from alsa_midi import READ_PORT, Address, MidiBytesEvent, SequencerClient


def make_events():
    # 3 ticks per quarternote, swung
    return [
            # D-on
            MidiBytesEvent(b"\x90\x3e\x7f", tick=0),

            # D-off, E-on
            MidiBytesEvent(b"\x80\x3e\x00\x90\x40\x7f", tick=2),

            # E-off, F-on
            MidiBytesEvent(b"\x80\x40\x00\x90\x41\x7f", tick=3),

            # F-off, G-on
            MidiBytesEvent(b"\x80\x41\x00\x90\x43\x7f", tick=5),

            # G-off, E-on
            MidiBytesEvent(b"\x80\x43\x00\x90\x40\x7f", tick=6),

            # E-off, C-on
            MidiBytesEvent(b"\x80\x40\x00\x90\x3c\x7f", tick=9),

            # C-off, D-on
            MidiBytesEvent(b"\x80\x3c\x00\x90\x3e\x7f", tick=11),

            # D-off
            MidiBytesEvent(b"\x80\x3e\x00", tick=24),
    ]


def main():
    parser = ArgumentParser(description="Play the lick (by sending bytes)")
    parser.add_argument("--port", "-p", type=Address, action="append",
                        help="Connect to the specific port(s)")
    parser.add_argument("--bpm", type=float, default=120.0,
                        help="Tempo in beats per minute (default: 120)")

    args = parser.parse_args()

    client = SequencerClient("play_the_lick.py")
    port = client.create_port("output", READ_PORT)
    queue = client.create_queue()

    queue.set_tempo(int(60.0 * 1000000 / args.bpm), 3)

    if args.port:
        targets = args.port
    else:
        target = client.list_ports(output=True)[0]
        print(f"Playing on {target.client_id}:{target.port_id}"
              f" '{target.name}' of '{target.client_name}'")
        targets = [target]

    for target in targets:
        port.connect_to(target)

    queue.start()
    try:
        for event in make_events():
            client.event_output(event, port=port, queue=queue)
        client.drain_output()
    except KeyboardInterrupt:
        pass

    time.sleep(60.0 * 8 / args.bpm)

    client.close()


if __name__ == '__main__':
    main()
