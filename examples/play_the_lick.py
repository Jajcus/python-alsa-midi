#!/usr/bin/env python3

import time
from argparse import ArgumentParser

from alsa_midi import READ_PORT, Address, NoteOffEvent, NoteOnEvent, SequencerClient


def make_events():
    # 3 ticks per quarternote, swung
    return [
            # D
            NoteOnEvent(62, tick=0),
            NoteOffEvent(62, tick=2),

            # E
            NoteOnEvent(64, tick=2),
            NoteOffEvent(64, tick=3),

            # F
            NoteOnEvent(65, tick=3),
            NoteOffEvent(65, tick=5),

            # G
            NoteOnEvent(67, tick=5),
            NoteOffEvent(67, tick=6),

            # E
            NoteOnEvent(64, tick=6),
            NoteOffEvent(64, tick=9),

            # C
            NoteOnEvent(60, tick=9),
            NoteOffEvent(60, tick=11),

            # D
            NoteOnEvent(62, tick=11),
            NoteOffEvent(62, tick=24),
    ]


def main():
    parser = ArgumentParser(description="Play the lick")
    parser.add_argument("--port", "-p", type=Address, action="append",
                        help="Connect to the specific port(s)")
    parser.add_argument("--bpm", type=float, default=120.0,
                        help="Tempo in beats per minute (default: 120)")

    args = parser.parse_args()

    client = SequencerClient("play_the_lick.py")
    port = client.create_port("output", READ_PORT)
    queue = client.create_queue()

    queue.set_tempo(bpm=args.bpm, ppq=3)

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
