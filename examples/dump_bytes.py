#!/usr/bin/env python3

from argparse import ArgumentParser

from alsa_midi import WRITE_PORT, Address, MidiBytesEvent, SequencerClient


def main():
    parser = ArgumentParser(description="Dump / sniff ALSA sequencer events as MIDI bytes (hex)")
    parser.add_argument("--real-time", action="store_true", default=None,
                        help="Force timestamps in seconds")
    parser.add_argument("--all-events", "-a", action="store_true",
                        help="Show events that are not MIDI messages")
    parser.add_argument("--port", "-p", type=Address, action="append",
                        help="Connect to the specific port")

    args = parser.parse_args()

    client = SequencerClient("dump_events.py")

    if args.real_time:
        queue = client.create_queue()
    else:
        queue = None

    port = client.create_port("input", WRITE_PORT,
                              timestamping=args.real_time,
                              timestamp_real=args.real_time,
                              timestamp_queue=queue)
    addr = Address(port)

    print(f"Listening for events at sequecncer port {addr}")

    if args.port:
        for target_port in args.port:
            port.connect_from(target_port)

    if queue is not None:
        queue.start()
        client.drain_output()

    time_h, source_h = "Time", "Source"
    if args.all_events:
        event_h = "Bytes / Event"
    else:
        event_h = "Bytes"
    print(f"{time_h:>15} {source_h:7} {event_h}")
    try:
        while True:
            event = client.event_input(prefer_bytes=True)
            if event is None:
                print("no event")
                continue
            if isinstance(event, MidiBytesEvent):
                event_s = " ".join(f"{b:02X}" for b in event.midi_bytes)
            elif args.all_events:
                event_s = repr(event)
            else:
                continue
            if event.time is not None:
                time_s = str(event.time)
            elif event.tick is not None:
                time_s = str(event.tick)
            else:
                time_s = ""
            print(f"{time_s:>15} {event.source!s:7} {event_s}")
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
