#!/usr/bin/env python3

from argparse import ArgumentParser

from alsa_midi import SequencerClient


def main():
    parser = ArgumentParser(description="List ALSA sequencer ports")
    parser.add_argument("--client-id", action="append", type=int,
                        help="Client to query")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show port details")

    args = parser.parse_args()

    client_ids = args.client_id

    client = SequencerClient("list_ports.py")

    client_names = {}

    client_info = client.query_next_client()
    while client_info:
        client_names[client_info.client_id] = client_info.name
        client_info = client.query_next_client(client_info)

    if client_ids is None:
        client_ids = list(client_names)

    for client_id in client_ids:
        client_name = client_names.get(client_id, "<unknown>")
        port_info = client.query_next_port(client_id)
        if not port_info:
            continue
        print(f"Client {client_id} {client_name!r}:")
        while port_info is not None:
            print(f"  {client_id}:{port_info.port_id} {port_info.name}")
            if args.verbose:
                print(f"    capabilities    : {port_info.capability!s}")
                print(f"    type            : {port_info.type!s}")
                print(f"    midi channels   : {port_info.midi_channels}")
                print(f"    midi voices     : {port_info.midi_voices}")
                print(f"    synth voices    : {port_info.synth_voices}")
                print(f"    read subs.      : {port_info.read_use}")
                print(f"    write subs.     : {port_info.write_use}")
                print(f"    timestamping    : {port_info.timestamping}")
                print(f"    timestamp real  : {port_info.timestamp_real}")
                print(f"    timestamp queue : {port_info.timestamp_queue_id}")

            port_info = client.query_next_port(client_id, port_info)

        print()


if __name__ == '__main__':
    main()
