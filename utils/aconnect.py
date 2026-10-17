#!/usr/bin/env python3

import argparse
import errno
import os
from pprint import pprint    # DEBUG
import re
import shutil
import sys
import textwrap

from alsa_midi import SequencerClient, \
                      Address, \
                      ALSAError, \
                      ClientType, \
                      SubscriptionQueryType

program_name = None
clients      = {}
ports        = {}



def direction(raw):
    # The perfection that is ALSA sequencer
    if   raw.name == 'INPUT' : return 'OUTPUT'
    elif raw.name == 'OUTPUT': return 'INPUT'
    else:                      return raw.name


def indent(text):
    indenter.subsequent_indent = " " * re.search(r"^.*'.*'\s*", text).span()[1]
    sys.stdout.write('%s\n' % indenter.fill(text))



def init(term_width):
    global program_name, aconnect, indenter
    aconnect = SequencerClient(program_name)
    width =      term_width      \
            if   term_width > 0  \
            else shutil.get_terminal_size().columns - 5
    indenter = textwrap.TextWrapper(width=width, break_long_words=False)



def get_clients(client_list=None):
    # Need include_system for client:port names of connections
    # from non-system to system clients.
    client_list = aconnect.list_clients(include_system=True,
                                        include_kernel=True)
    for client in client_list:
        if client.name != program_name:
            clients[client.client_id] = client



def get_ports():
    global aconnect, ports

    # Need ports for system clients in to get client:port names
    # for non-system ports connected to system ones.
    port_list = aconnect.list_ports(include_system=True,
                                    include_kernel=True,
                                    type=None,
                                    only_connectable=False)

    for port in port_list:
        ports.setdefault(port.client_id, {})
        ports[port.client_id][port.port_id] = port



def print_connections(client, address):
    for sub in aconnect.list_port_subscribers(address):
        # other = sub.addr
        sub_clnt = clients[sub.addr.client_id].name
        sub_port = ports[sub.addr.client_id][sub.addr.port_id].name
        if sub.type == SubscriptionQueryType.READ:
            sys.stdout.write( "\tconnected to "
                             f"'{sub_clnt}:{sub_port}'"
                             f"({sub.addr})\n")
        elif sub.type == SubscriptionQueryType.WRITE:
            sys.stdout.write( "\tconnected from "
                             f"'{sub_clnt}:{sub_port}'"
                             f"({sub.addr})\n")



def report(clients_only     = False,
           all_clients      = False,
           pipewire_clients = False,
           full_info        = False):
    global aconnect, clients, ports

    if not clients:
        get_clients()

    if clients_only:
        ports = None
        max_name_len = max([len(client.name) for client in clients.values()])
        max_type_len = max([    len(client.type.name)
                            for client
                            in  clients.values()])
    else:
        if not ports:
            get_ports()
        max_port_len = max([    len(port.name)
                            for portval in ports.values()
                            for port
                            in  portval.values()
                            if  not (     not all_clients
                                     and
                                             clients[port.client_id].type
                                          ==  ClientType.KERNEL)
                           ])

    for (client_id, client) in clients.items():
        # if client.name == program_name:
        #   continue

        if client.type == ClientType.KERNEL and not all_clients:
            continue

        if 'PipeWire' in client.name and not pipewire_clients:
            continue

        # If all ports are of same type report on client line
        port_type = None
        if ports and client_id in ports and len(ports[client_id].values()) > 0:
            port_type_0 = list(ports[client_id].values())[0].type
            # pprint([port.type for port in ports[client_id].values()])
            if all(    port.type == port_type_0
                   for port
                   in  ports[client_id].values()):
                port_type = port_type_0

        if clients_only:
            client_str = f"{client_id:>3}: {client.name!r:<{max_name_len+4}}"
            if full_info:
                client_str +=   f"{client.type.name} "          \
                              + f"ports={client.num_ports} "    \
                              + f"pid={client.pid}"
            else:
                client_str +=   f"{client.type.name:<{max_type_len}}  " \
                              + f"ports={client.num_ports:<3} "         \
"pid={client.pid}"
        else:
            client_str = f"{client_id}: '{client.name}' "       \
                         f"{client.type.name} pid={client.pid}"

        if port_type is not None:
            client_str += f" ports={port_type.name}"

        if full_info:
            indent(f"{client_str} "
                   f"event_filter={client.event_filter} "
                   f"broadcast_filter={client.broadcast_filter} "
                   f"error_bounce={client.error_bounce} "
                   f"event_lost={client.event_lost} "
                   f"card_id={client.card_id} "
                   f"num_ports={client.num_ports}")
        else:
            indent(f"{client_str}\n")

        if ports and client_id in ports:
            for port in ports[client_id].values():
                port_str = (f"  {port.port_id:>3}: "
                            f"{port.name!r:<{max_port_len+3}} "
                            f"{direction(port.direction)}")
                if port_type is None:
                    port_str += f" {port_type.name}"
                if full_info:
                    indent(f"{port_str} "
                           f"capability={port.capability.name} "
                           f"client_id={port.client_id} "
                           f"midi_channels={port.midi_channels} "
                           f"midi_voices={port.midi_voices} "
                           f"port_specified={port.port_specified} "
                           f"read_use={port.read_use} "
                           f"synth_voices={port.synth_voices} "
                           f"timestamp_queue_id= "
                           f"{port.timestamp_queue_id} "
                           f"timestamp_real={port.timestamp_real} "
                           f"timestamping={port.timestamping} "
                           f"write_use={port.write_use}")
                else:
                    sys.stdout.write(f"{port_str}\n")
                print_connections(client, Address(port.client_id, port.port_id))



def connect_disconnect(disconnect, source, sink, exclusive=None, real=None):
    "Connect or disconnect client:port to/from another_client:another_port"

    global aconnect

    source_addr = aconnect.resolve_address(source)
    sink_addr   = aconnect.resolve_address(sink  )

    if disconnect:
        try:
            aconnect.unsubscribe_port(source_addr, sink_addr)
        except ALSAError as e:
            raise ALSAError(f"Can't disconnect {source} -> {sink} "
                             "(not connected?)",
                            errno.EINVAL)
    else:
        try:
            aconnect.subscribe_port(source_addr,
                                    sink_addr,
                                    exclusive=opts.exclusive,
                                    time_update=(opts.real is not None),
                                    time_real=opts.real)
        except ALSAError as e:
            raise ALSAError(f"Can't connect {source} -> {sink} "
                         "(input->output?) (or already connected?)",
                        errno.ENOENT)



def disconnect(client, no_safety):
    "Disconnect all ports of one client"

    global aconnect, clients, ports

    # check that is just client (no port)
    if not isinstance(client, int):
        assert not any(char in client for char in '.:'), \
               "Specify client, not client:port"

    # Can't use aconnect.resolve_address() because no port specified
    # and client might not have default port 0.
    if isinstance(client, int):
        client_id   = client
        client_name = str(client)
    else:
        client_name = client
        try:
            client_id = int(client)
        except ValueError:
            client_id = None

    client_list = aconnect.list_clients(include_system=True,
                                        include_kernel=True)
    found_id    = None
    for search in client_list:
        if client_id is not None and search.client_id == client_id:
            found_id = search.client_id
            break
        elif search.name == client_name:
            found_id = search.client_id
            break

    assert found_id is not None,                    \
                f"No client named '{client_name}'"  \
           if   client_id is None                   \
           else f"No client number {client_id}"

    if not clients: get_clients(client_list)
    if not ports:   get_ports()

    if                          found_id        == 0                        \
       or               clients[found_id].type == ClientType.KERNEL \
       or 'PipeWire' in clients[found_id].name:
        raise ALSAError(f"Can't disconnect client {found_id}'s ports "
                         "(is system, KERNEL, and/or PipeWire)",
                        errno.EINVAL)

    if not no_safety:
        max_port_len = max([    len(port.name)
                            for port
                            in  ports[found_id].values()])
        for port in ports[found_id].values():
            sys.stdout.write(f"  {port.port_id:>3}: "
                             f"{port.name!r:<{max_port_len+3}} "
                             f"{direction(port.direction)}\n")
            print_connections(clients[found_id],
                              Address(found_id, port.port_id))
        if input("Remove all (if any) connections? n/Y: ") != 'Y':
            sys.stdout.write("Aborting\n")
            return

    for port in ports[found_id].values():
        address = Address(found_id, port.port_id)
        for sub in aconnect.list_port_subscribers(address):
            sub_clnt = clients[sub.addr.client_id].name
            sub_port = ports[sub.addr.client_id][sub.addr.port_id].name
            if sub.type == SubscriptionQueryType.READ:
                connect_disconnect(True, address, sub.addr)
            elif sub.type == SubscriptionQueryType.WRITE:
                connect_disconnect(True, sub.addr, address)



def remove_all(no_safety):
    global aconnect, program_name

    if not no_safety:
        report()
        if input("Remove all (if any) connections? n/Y: ") != 'Y':
            sys.stdout.write("Aborting\n")
            return

    for client in aconnect.list_clients(include_system=False,
                                        include_kernel=False):
        if client.name == program_name or "PipeWire" in client.name:
            continue
        disconnect(client.client_id, no_safety=True)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="List, connect, disconnect "
                                                 "ALSA ports")

    parser.add_argument('-d', '--disconnect',
                        action="store_true",
                        help="Disconnect existing one connection or "
                             "all of one client's connections")
    parser.add_argument('-D', '--DISCONNECT',
                        action="store_true",
                        help="Disconnect all of one client's connections "
                             "without 'Are you sure?'")
    parser.add_argument('-x', '--removeall',
                        action='store_true',
                        help="Disconnect all clients/ports connections")
    parser.add_argument('-X', '--REMOVEALL',
                        action='store_true',
                        help="Disconnect all clients/ports connections "
                             "without 'Are you sure?'")
    parser.add_argument('-e', '--exclusive',
                        action='store_true',
                        help="Exclusive connection")
    parser.add_argument('-r', '--real',
                        action='store_true',
                        help="Use real-time-stamp")
    parser.add_argument('-t', '--tick',
                        action='store_false',
                        dest='real',
                        help="Use tick-time-stamp")

    parser.add_argument('-c', '--clients',
                        action='store_true',
                        help="list only clients (no port info)")
    parser.add_argument('-i', '--input',
                        action='store_true',
                        help="list input (readable) ports")
    parser.add_argument('-o', '--output',
                        action='store_true',
                        help="list output (writable) ports")
    parser.add_argument('-a', '--all',
                        action='store_true',
                        help="include kernel/system clients and ports")
    parser.add_argument('-p', '--pipewire',
                        action='store_true',
                        help="include pipewire clients and ports")
    parser.add_argument('-f', '--full',
                        action='store_true',
                        help="full client and port info")
    parser.add_argument('-w', '--width',
                        type=int,
                        default=0,
                        help="override terminal width (or provide if "
                             "not tty) if not 0")

    parser.add_argument('source',
                        nargs='?',
                        metavar='CLIENT:PORT',
                        help="Source side of the connection")
    parser.add_argument('dest',
                        nargs='?',
                        metavar='CLIENT:PORT',
                        help="Sink side of the connection")

    try:
        program_name = os.path.basename(sys.argv[0])
        opts         = parser.parse_args()
        # pprint(opts)    # DEBUG
        if opts.DISCONNECT: opts.disconnect = True
        if opts.REMOVEALL:  opts.removeall  = True


        init(opts.width)

        if opts.source:
            if opts.dest:
                connect_disconnect(opts.disconnect,
                                   opts.source,
                                   opts.dest,
                                   opts.exclusive,
                                   opts.real)
            else:
                disconnect(opts.source, opts.DISCONNECT)
        elif opts.removeall:
            remove_all(opts.REMOVEALL)
        else:
            report(opts.clients, opts.all, opts.pipewire, opts.full)
            sys.stdout.write(f"'{program_name} -h' for options\n")
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)

    sys.exit(0)
