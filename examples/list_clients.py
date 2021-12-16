#!/usr/bin/env python3

from alsa_midi import SequencerClient


def main():
    client = SequencerClient("list_clients.py")

    client_info = client.query_next_client()
    while client_info:
        print(f"Client {client_info.client_id}: {client_info.name!r}")
        assert client_info.type is not None
        print(f"  type             : {client_info.type.name}")
        if client_info.card_id is not None:
            print(f"  card             : {client_info.card_id}")
        if client_info.pid is not None:
            print(f"  pid              : {client_info.pid}")
        # print(f"  broadcast filter : {client_info.broadcast_filter}")
        # print(f"  error bounce     : {client_info.error_bounce}")
        print(f"  number of ports  : {client_info.num_ports}")
        print(f"  events lost      : {client_info.event_lost}")

        print()
        client_info = client.query_next_client(client_info)


if __name__ == '__main__':
    main()
