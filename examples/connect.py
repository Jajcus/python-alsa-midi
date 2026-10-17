#!/usr/bin/env python3

from argparse import ArgumentParser

from alsa_midi import Address, SequencerClient


def main():
    parser = ArgumentParser(description="Connect or disconnect alsa ports")
    parser.add_argument("--disconnect", "-d", action="store_true",
                        help="Disconnect existing connection")
    parser.add_argument("--exclusive", "-e", action="store_true", default=False,
                        help="Exclusive connection")
    parser.add_argument("--real", "-r", action="store_true",
                        help="Use real-time-stamp")
    parser.add_argument("--tick", "-t", action="store_false", dest="real",
                        help="Use tick-time-stamp")
    parser.add_argument("sender", type=Address, metavar="CLIENT:PORT",
                        help="Source side of the connection")
    parser.add_argument("dest", type=Address, metavar="CLIENT:PORT",
                        help="Sink side of the connection")

    args = parser.parse_args()

    client = SequencerClient("dump_events.py")

    if args.disconnect:
        client.unsubscribe_port(args.sender, args.dest)
    else:
        client.subscribe_port(args.sender, args.dest,
                              exclusive=args.exclusive,
                              time_update=(args.real is not None),
                              time_real=args.real)


if __name__ == '__main__':
    main()
