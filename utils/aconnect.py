#!/usr/bin/env python3

import argparse
import errno
import os
import re
import shutil
import sys
import textwrap

from alsa_midi import SequencerClient,      \
    Address,              \
    ALSAError,            \
    ClientInfo,           \
    ClientType,           \
    PortDirection,        \
    PortInfo,             \
    PortType,             \
    SubscriptionQueryType

program_name: str = ""
aconnect:     SequencerClient
clients:      dict[int,      ClientInfo] = {}  # client_id: CLientInfo
ports:        dict[int, list[PortInfo]] = {}  # client_id: [PortInfos]
indenter:     textwrap.TextWrapper


def direction(raw: PortDirection) -> str:
    "ALSA names for input vs output are backwards."
    if raw.name == 'INPUT':
        return 'OUTPUT'
    elif raw.name == 'OUTPUT':
        return 'INPUT'
    elif raw.name is None:
        return '???'
    else:
        return raw.name


def indent(text: str) -> None:
    "Indent lines after first line to past ID and padded name."
    dot_star = re.search(r"^.*'.*'\s*", text)
    if dot_star is not None:
        indenter.subsequent_indent = " " * dot_star.span()[1]
    sys.stdout.write('%s\n' % indenter.fill(text))


def init(term_width: int) -> None:
    "Inititialize global client and textwrap object."
    global program_name, aconnect, indenter
    aconnect = SequencerClient(program_name)
    width = term_width      \
        if term_width > 0  \
        else shutil.get_terminal_size().columns - 5
    indenter = textwrap.TextWrapper(width=width, break_long_words=False)


def get_clients(client_list: list[ClientInfo] | None = None) -> None:
    """Populate clients dict with provided or function-fetched
    list of ClientInfos.
    """

    if client_list is None:  # caller may have already fetched
        # Need include_system for client:port names of connections
        # from non-system to system clients.
        client_list = aconnect.list_clients(include_system=True,
                                            include_kernel=True)
    for client in client_list:
        if client.name != program_name:
            clients[client.client_id] = client


def get_ports() -> None:
    "Populate ports dict"
    global aconnect, ports

    # Need ports for system clients in to get client:port names
    # for non-system ports connected to system ones.
    port_list = aconnect.list_ports(include_system=True,
                                    include_kernel=True,
                                    type=PortType.ANY,
                                    only_connectable=False)

    for port in port_list:
        ports.setdefault(port.client_id, [])
        ports[port.client_id].append(port)


def print_client(client:       ClientInfo,
                 client_id:    int,
                 max_name_len: int = 0,
                 max_type_len: int = 0,
                 client_only:  bool = False,
                 inputs_only:  bool = False,
                 outputs_only: bool = False,
                 full_info:    bool = False):
    """Print info for single client, with/without port and or full
    information.

    :param client:       client to print
    :param client_id:    ID of client
    :param max_name_len: maximum length of port (normal) or
                         client (clients_only) names
    :param max_name_len: maximum length of client type strings
    :param client_only:  do not print client's ports
    :param inputs_only:  print only input ports
    :param outputs_only: print only output ports
    :param full_info:    print full client and port info

    :return: Total number of connections for all ports of client
    """

    global ports

    if not client_only and not ports:
        get_ports()

    # If all ports are of same type report on client line
    port_type = None
    if ports and client_id in ports and len(ports[client_id]) > 0:
        port_type_0 = ports[client_id][0].type
        if all(port.type == port_type_0 for port in ports[client_id]):
            port_type = port_type_0

    client_type_name = "" if client.type is None else client.type.name

    if client_only:
        client_str = f"{client_id:>3}: {client.name!r:<{max_name_len+4}}"
        if full_info:
            client_str += f"{client_type_name:<{max_type_len}} "  \
                + f"ports={client.num_ports} "            \
                + f"pid={client.pid}"
        else:
            client_str += f"{client_type_name:<{max_type_len}}  " \
                + f"ports={client.num_ports:<3} "         \
                f"pid={client.pid}"
    else:
        client_str = f"{client_id}: '{client.name}' "       \
            f"{client_type_name} pid={client.pid}"

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

    if client_only:
        return 0

    num_connections = 0
    if ports and client_id in ports:
        for port in ports[client_id]:
            if inputs_only and port.direction == PortDirection.INPUT:   # sic
                continue
            if outputs_only and port.direction == PortDirection.OUTPUT:  # sic
                continue
            port_str = (f"  {port.port_id:>3}: "
                        f"{port.name!r:<{max_name_len+3}} "
                        f"{direction(port.direction)}")
            if port_type is None:
                port_str += f" {port.type.name}"
            if full_info:
                indent(f"{port_str} "
                       f"capability={port.capability.name} "
                       f"client_id={port.client_id} "
                       f"midi_channels={port.midi_channels} "
                       f"midi_voices={port.midi_voices} "
                       f"read_use={port.read_use} "
                       f"synth_voices={port.synth_voices} "
                       f"timestamp_queue_id= "
                       f"{port.timestamp_queue_id} "
                       f"timestamp_real={port.timestamp_real} "
                       f"timestamping={port.timestamping} "
                       f"write_use={port.write_use}")
            else:
                sys.stdout.write(f"{port_str}\n")
            if port.port_id is not None:
                num_connections += print_connections(Address(port.client_id,
                                                             port.port_id),
                                                     full_info)
    return num_connections


def print_connections(address:   Address,
                      full_info: bool = False) -> int:
    """Print port's connections.
    :return: Number of connections
    """
    global indenter

    subs = aconnect.list_port_subscribers(address)
    for sub in subs:
        sub_clnt = clients[sub.addr.client_id].name
        sub_port = next((port
                         for port
                         in ports[sub.addr.client_id]
                         if port.port_id == sub.addr.port_id),
                        None)
        sub_port_name = "???" if sub_port is None else sub_port.name
        if sub.type == SubscriptionQueryType.READ:
            text = ("\tconnected to "
                    f"'{sub_clnt}:{sub_port_name}'"
                    f"({sub.addr})")
            indenter.subsequent_indent = " " * 21    # len("\tconnected to ")
        elif sub.type == SubscriptionQueryType.WRITE:
            text = ("\tconnected from "
                    f"'{sub_clnt}:{sub_port_name}'"
                    f"({sub.addr})")
            indenter.subsequent_indent = " " * 23    # len("\tconnected from ")
        if sub.time_update or sub.time_real:
            text += f" real queue={sub.queue_id}"
        if full_info:
            text += (f" root={sub.root}"
                     f" index={sub.index}"
                     f" num_subs={sub.num_subs}"
                     f" addr={sub.addr}"
                     f" queue_id={sub.queue_id}"
                     f" exclusive={bool(sub.exclusive)}"
                     f" time_update={bool(sub.time_update)}"
                     f" time_real={bool(sub.time_real)}")
        sys.stdout.write('%s\n' % indenter.fill(text))
    return len(subs)


def print_clients(
    client_list:      list[str] = [],
    clients_only:     bool = False,
    kernel_clients:   bool = False,
    pipewire_clients: bool = False,
    inputs_only:      bool = False,
    outputs_only:     bool = False,
    full_info:        bool = False  # print additional client+port info
) -> int:
    """Print all clients. See print_client().
    :param client_list:         list of clients to print (or all if empty)
    :param clients_only:        don't print port info
    :param kernel_clients:      include system and kernel clients
    :param pipewire_clients:    include pipewire clients
    :inputs_only:               only input ports
    :outputs_only:              only output ports
    :param full_info:           print additional client+port info

    :return: Total number of connections for all ports of all clients
    """

    global aconnect, clients, ports

    if not clients:
        get_clients()

    if not clients_only:
        get_ports()

    if client_list:
        client_ids = []
        for client_arg in client_list:
            colons = client_arg.replace('.', ':')
            splits = colons.split(':')
            assert len(splits) <= 2, \
                f"Bad client or client:port \"{client_arg}\""
            client_arg = splits[0]
            client_id: int | None
            if client_arg.isdigit():
                client_id = int(client_arg)
            else:
                client_id = next((client_id
                                  for (client_id, client_info)
                                  in clients.items()
                                  if client_arg in client_info.name),
                                 None)
                assert client_id is not None, \
                    f"Can't find client \"{client_arg}\""
            client_ids.append(client_id)
    else:
        client_ids = list(clients.keys())

    displayed_clients = []
    max_name_len = 0
    max_type_len = 0
    for client_id in client_ids:
        client = clients[client_id]
        if client.type == ClientType.KERNEL and not kernel_clients:
            continue
        if 'PipeWire' in client.name and not pipewire_clients:
            continue
        displayed_clients.append(client_id)
        client_type_name = "" if client.type is None else client.type.name
        if len(client_type_name) > max_type_len:
            max_type_len = len(client_type_name)
        if clients_only:
            if len(client.name) > max_name_len:
                max_name_len = len(client.name)
        else:
            max_client_port_len = max([len(port.name)
                                       for port
                                       in ports[client_id]])
            if max_client_port_len > max_name_len:
                max_name_len = max_client_port_len

    if not displayed_clients:
        return 0

    num_connections = 0
    for client_id in displayed_clients:
        num_connections += print_client(clients[client_id],
                                        client_id,
                                        max_name_len,
                                        max_type_len,
                                        clients_only,
                                        inputs_only,
                                        outputs_only,
                                        full_info)
    return num_connections


def connect(clients_ports:  list[str],
            exclusive:      bool = False,
            time_real:      bool = False,
            time_update:    bool = False,
            queue:          int = 0) -> None:
    "Connect one client:port to or from another_client:another_port"

    global aconnect

    assert len(clients_ports) == 2, \
        "Must have exactly two clients:ports to connect"

    source = clients_ports[0]
    sink = clients_ports[1]

    try:
        source_addr = aconnect.resolve_address(source)
        sink_addr = aconnect.resolve_address(sink)
    except ALSAError as e:
        raise ALSAError("Bad or non-existent source and/or sink", errno.ENOENT)

    try:
        aconnect.subscribe_port(source_addr,
                                sink_addr,
                                queue=queue,
                                exclusive=exclusive,
                                time_update=time_update,
                                time_real=time_real)
    except ALSAError as e:
        raise ALSAError(f"Can't connect {source}({source_addr}) -> "
                        f"{sink}({sink_addr}) (not output->input? "
                        "already connected?)",
                        errno.ENOENT)


def disconnect(clients_ports: list[str],
               no_safety:     bool) -> None:
    """"Disconnect a single connection between two ports, all connections
    to/from a single port, all connections to/from all of a single
    client's ports, or all connections.

    :param no_safety: Do not print connections to be removed and input
                      user confirmation (not used for single connection
                      between two ports case).

    """

    if not clients_ports:
        remove_all_connections(no_safety)
    elif len(clients_ports) == 1:
        if '.' in clients_ports[0] or ':' in clients_ports[0]:
            remove_port_connections(clients_ports[0], no_safety)
        else:
            remove_client_connections(clients_ports[0], no_safety)
    elif len(clients_ports) == 2:
        remove_connection(*clients_ports)
    else:
        raise TypeError("-d,--disconnect requires 0, 1, or 2 arguments.")


def remove_connection(source: str | Address,
                      sink:   str | Address):
    "Disconnect single clientA:portA -> clientB:portB connection."

    global aconnect

    try:
        source_addr = aconnect.resolve_address(source)
        sink_addr = aconnect.resolve_address(sink)
    except ALSAError as e:
        raise ALSAError("Bad or non-existent source and/or sink", errno.EINVAL)

    try:
        aconnect.unsubscribe_port(source_addr, sink_addr)
    except ALSAError as e:
        raise ALSAError(f"Can't disconnect {source}->{sink} "
                        f"(not connected? or reversed {sink}->"
                        f"{source}?)",
                        errno.EINVAL)


def remove_port_connections(client_port: str,
                            no_safety:   bool) -> None:
    """"Remove all connections to/from one client:port

    :param no_safety: Do not print connections to be removed and input
                      user confirmation.
    """

    global aconnect, clients, ports

    try:
        address = aconnect.resolve_address(client_port)
    except Exception as e:
        raise ALSAError(f"Bad or non-existent client:port '{client_port}'",
                        errno.EINVAL)

    if not no_safety:
        if not clients:
            get_clients()
        if not ports:
            get_ports()

        max_port_len = max([len(port.name)
                            for port
                            in ports[address.client_id]])

        print_client(clients[address.client_id],
                     address.client_id,
                     client_only=True)

        port = next((port
                     for port
                     in ports[address.client_id]
                     if port.port_id == address.port_id),
                    None)
        assert port is not None, \
            f"{program_name}: Internal error, can't find port."

        sys.stdout.write(f"  {port.port_id:>3}: "
                         f"{port.name!r:<{max_port_len+3}} "
                         f"{direction(port.direction)}\n")
        count = print_connections(address)

        if count == 0:
            sys.stdout.write("No connections to delete\n")
            return

        if input(f"Remove {count} connection(s)? n/Y: ") != 'Y':
            sys.stdout.write("Aborting\n")
            return

    for sub in aconnect.list_port_subscribers(address):
        if sub.type == SubscriptionQueryType.READ:
            remove_connection(address, sub.addr)
        elif sub.type == SubscriptionQueryType.WRITE:
            remove_connection(sub.addr, address)


def remove_client_connections(client:    str | int,
                              no_safety: bool) -> None:
    """Remove all connections to/from all of one client's ports

    :param no_safety: Do not print connections to be removed and input
                      user confirmation.
    """

    global aconnect, clients, ports

    # check that is just client (no port)
    if not isinstance(client, int):
        assert not any(char in client for char in '.:'), \
            "Specify client, not client:port"

    # Can't use aconnect.resolve_address() because no port specified
    # and client might not have default port 0.
    if isinstance(client, int):
        client_id = client
        client_name = str(client)
    else:
        client_name = client
        try:
            client_id = int(client)
        except ValueError:
            client_id = None

    client_list = aconnect.list_clients(include_system=True,
                                        include_kernel=True)
    found_id = None
    for search in client_list:
        if client_id is not None and search.client_id == client_id:
            found_client = search
            found_id = search.client_id
            break
        elif search.name.startswith(client_name):
            found_client = search
            found_id = search.client_id
            break

    assert found_id is not None,                    \
        f"No client named '{client_name}'"  \
        if client_id is None                   \
        else f"No client number {client_id}"

    if not clients:
        get_clients(client_list)
    if not ports:
        get_ports()

    if found_id == 0                        \
       or clients[found_id].type == ClientType.KERNEL \
       or 'PipeWire' in clients[found_id].name:
        raise ALSAError(f"Can't disconnect client {found_id}'s ports "
                        "(is system, KERNEL, and/or PipeWire)",
                        errno.EINVAL)

    if not no_safety:
        max_port_len = max([len(port.name) for port in ports[found_id]])
        count = print_client(found_client, found_id, max_port_len)

        if count == 0:
            sys.stdout.write("No connections to delete\n")
            return

        if input(f"Remove all {count} connection(s)? n/Y: ") != 'Y':
            sys.stdout.write("Aborting\n")
            return

    for port in ports[found_id]:
        if port.port_id is None:
            continue
        address = Address(found_id, port.port_id)
        for sub in aconnect.list_port_subscribers(address):
            if sub.type == SubscriptionQueryType.READ:
                remove_connection(address, sub.addr)
            elif sub.type == SubscriptionQueryType.WRITE:
                remove_connection(sub.addr, address)


def remove_all_connections(no_safety: bool) -> None:
    """"Remove all connections between all ports of all clients.
    :param no_safety: Do not print connections to be removed and input
                      user confirmation.
    """

    global aconnect, program_name

    if not no_safety:
        count = print_clients()
        if count == 0:
            sys.stdout.write("No connections to delete\n")
            return
        if input(f"Remove all {count} connection(s)? n/Y: ") != 'Y':
            sys.stdout.write("Aborting\n")
            return

    for client in aconnect.list_clients(include_system=False,
                                        include_kernel=False):
        if client.name == program_name or "PipeWire" in client.name:
            continue
        remove_client_connections(client.client_id, no_safety=True)


if __name__ == '__main__':
    DESCRIPTION = """List, connect, disconnect ALSA ports.
                  Specify 'client:port' or 'client.port' by numeric IDs or
                  names, or 'client' for no port or implicit port 0. List
                  clients with ports (or without if -c,--clients) if 0, 1,
                  or 3+ clients:ports. Connect two client:ports unless
                  -d,--delete or -D,--DELETE.
                  """

    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument('-d', '--disconnect',
                        action="store_true",
                        help="Disconnect one existing connection ('clientA:"
                             "portA clientB:PortB'), all connections to/from "
                             "a port ('client:port'), all connections to/from "
                             "a client's ports ('client'), or all connections "
                             "(no clients,ports specified)")
    parser.add_argument('-D', '--DISCONNECT',
                        action="store_true",
                        help="Same as -d,--delete without listing connections "
                             "to be disconnected and requiring 'n/Y' "
                             "response. Implicit if -d,--delete with two "
                             "clients:ports.")

    parser.add_argument('-e', '--exclusive',
                        action='store_true',
                        help="Add exclusive to connect.")
    parser.add_argument('-u', '--update',
                        action='store_true',
                        help="Add time_update to connect.")
    parser.add_argument('-r', '--real',
                        action='store_true',
                        help="Add time_real to connect.")
    parser.add_argument('-q', '--queue',
                        type=int,
                        default=0,
                        help="Specify queue ID to connect.")

    parser.add_argument('-l', '--list',
                        action='store_true',
                        help="List clients (implicit if 0, 1, or 3+ clients).")
    parser.add_argument('-c', '--clients',
                        action='store_true',
                        help="List only clients (no ports)")
    parser.add_argument('-i', '--inputs',
                        action='store_true',
                        help="List only input (readable) ports")
    parser.add_argument('-o', '--outputs',
                        action='store_true',
                        help="List only output (writable) ports")
    parser.add_argument('-k', '--kernel',
                        action='store_true',
                        help="Include kernel/system clients")
    parser.add_argument('-p', '--pipewire',
                        action='store_true',
                        help="Include pipewire clients")
    parser.add_argument('-a', '--all',
                        action='store_true',
                        help="Include all (-k,-p) clients")
    parser.add_argument('-f', '--full',
                        action='store_true',
                        help="Full client and port info")
    parser.add_argument('-w', '--width',
                        type=int,
                        default=0,
                        help="Override terminal width (or provide if "
                             "not tty) if not 0")

    parser.add_argument('addresses',
                        nargs='*',
                        metavar="CLIENT[:PORT] ...",
                        help="Clients or client:ports")

    try:
        program_name = os.path.basename(sys.argv[0])
        opts = parser.parse_args()

        if opts.DISCONNECT:
            opts.disconnect = True
        if opts.all:
            opts.kernel = True
            opts.pipewire = True

        init(opts.width)

        if opts.disconnect:
            disconnect(opts.addresses, opts.DISCONNECT)
        elif len(opts.addresses) == 2 and not opts.list:
            connect(opts.addresses,
                    opts.exclusive,
                    opts.real,
                    opts.update,
                    opts.queue)
        else:
            print_clients(opts.addresses,
                          opts.clients,
                          opts.kernel,
                          opts.pipewire,
                          opts.inputs,
                          opts.outputs,
                          opts.full)
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        sys.stderr.write(f"'{program_name} -h' for help and options\n")
        sys.exit(1)

    sys.exit(0)
