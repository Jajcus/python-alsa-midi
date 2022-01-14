#!/usr/bin/env python3

from argparse import ArgumentParser, ArgumentTypeError

from alsa_midi import WRITE_PORT, Address, Event, EventType, SequencerClient

EVENT_NAMES = {t.name.lower(): t for t in EventType if t != EventType.NONE}
ALL_EVENT_NAMES = {k.replace("_", ""): v for k, v in EVENT_NAMES.items()}
ALL_EVENT_NAMES.update({v.__name__.replace("Event", "").lower(): k
                        for k, v in Event._specialized.items()})


def event_type(value):
    try:
        int_value = int(value)
        return EventType(int_value)
    except ValueError:
        pass
    value = value.lower().replace("_", "").replace(" ", "").replace("event", "")
    try:
        return ALL_EVENT_NAMES[value]
    except KeyError:
        raise ArgumentTypeError("Invalid event type. Valid options: " + ",".join(EVENT_NAMES))


def main():
    parser = ArgumentParser(description="Dump / sniff ALSA sequencer events")
    parser.add_argument("--real-time", action="store_true", default=None,
                        help="Force timestamps in seconds")
    parser.add_argument("--port", "-p", type=Address, action="append",
                        help="Connect to the specific port")
    parser.add_argument("--filter", "-f", type=event_type, action="append",
                        help="Event type to allow")

    args = parser.parse_args()

    client = SequencerClient("dump_events.py")

    if args.real_time:
        queue = client.create_queue()
    else:
        queue = None

    if args.filter:
        for e_type in args.filter:
            client.set_client_event_filter(e_type)

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

    time_h, source_h, event_h = "Time", "Source", "Event"
    print(f"{time_h:>15} {source_h:7} {event_h}")
    try:
        while True:
            event = client.event_input()
            if event is None:
                print("no event")
                continue
            if event.time is not None:
                time_s = str(event.time)
            elif event.tick is not None:
                time_s = str(event.tick)
            else:
                time_s = ""
            print(f"{time_s:>15} {event.source!s:7} {event!r}")
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
