import argparse
import sys

from collections import namedtuple

import alsa_midi
from alsa_midi import Address



"""Tests SequencerClientBase.get_address()

Tests many permutations of "numeric-or-named-client:numeric-or-named-port",
"client:port", "client.port", "'client:port'", (client, port), ((client, port)),
etc.

Runs silently by default, returns 0 on all tests successful or raised
expected exception. Otherwise exits with uncaught exception.

-v/--verbose option to output results and fail-with-expected-errors
-p/--pause to pause until killed (to use `aconnect -oil` to view test
           client/ports

Outputs test/pass/fail counts if either -v or -p
"""


test_count = 0      # total number of permutations tested
pass_count = 0      # successful tests
fail_count = 0      # test which failed with expected error


# clients/ports for tests
#

# port name, requested port id, actual port id, test substrings, capabilities
port_spec = namedtuple('port_spec', "name req_id id substr caps")

# mixture of capabilities (not used, but to make sure don't affect results)
INPUT_CAPS  = alsa_midi.WRITE_PORT
OUTPUT_CAPS = alsa_midi.READ_PORT
IN_OUT_CAPS = INPUT_CAPS | OUTPUT_CAPS

# all tests use this for client.get_address(...)
tester_ports = (
    port_spec("zero",   -1,     0,  False,  IN_OUT_CAPS),
)

# default sequentially-numbered ports
# tests port can be accessed by substring of name
sequential_ports = (
    port_spec("zero",   -1,     0,  False,  INPUT_CAPS  ),
    port_spec("One",    -1,     1,  False,  OUTPUT_CAPS ),
    port_spec("two"  ,  -1,     2,  False,  IN_OUT_CAPS ),
    port_spec("three",  -1,     3,  True,   OUTPUT_CAPS ),   # test by substring
    port_spec("FOUR" ,  -1,     4,  False,  INPUT_CAPS  ),
    port_spec("five" ,  -1,     5,  False,  IN_OUT_CAPS ),
)

# find above ports by substrings of names
prefix_ports = (
    port_spec("er",     -1,     0,  False,  IN_OUT_CAPS ),
    port_spec("On",     -1,     1,  False,  INPUT_CAPS  ),
    port_spec("wo",     -1,     2,  False,  OUTPUT_CAPS ),
)

# explicit non-default, non-sequential port numbers
# tests exact match of port name overrides substring match
explicit_ports = (
    port_spec("THREE",   3,     3,  False,  OUTPUT_CAPS ),
    port_spec("six",     6,     6,  False,  INPUT_CAPS  ),
    port_spec("Eight",   8,     8,  False,  IN_OUT_CAPS ),
    port_spec("ele",    12,    12,  False,  INPUT_CAPS  ),   # exact match
    port_spec("lev",    13,    13,  False,  INPUT_CAPS  ),   #   "    "
    port_spec("eleven", 11,    11,  False,  INPUT_CAPS  ),
    port_spec("eve",    14,    14,  False,  INPUT_CAPS  ),   # exact match
    port_spec("ven"  ,  15,    15,  False,  INPUT_CAPS  ),   #   "    "
    port_spec("twenTY", 20,    20,  False,  OUTPUT_CAPS ),
)



# at program exit if -v/--verbose, -p/--pause, or uncaught exception
def print_stats(stream=sys.stdout):
    global test_count, pass_count, fail_count
    stream.write(  "%d tests\n"
                   "%d passed\n"
                   "%d failed with expected errors  \n"
                 % (test_count,
                    pass_count,
                    fail_count))



# create clients/ports ports from above tuples of port_specs
def create_ports(client, port_descs):
    global clients_ports

    client_name = client.get_client_info().name

    for port_desc in port_descs:
        if port_desc.req_id == -1:
            port = client.create_port(name=port_desc.name,
                                      caps=port_desc.caps)
        else:
            port = client.create_port(name=port_desc.name,
                                      caps=port_desc.caps,
                                      port_id=port_desc.req_id)
        clients_ports.setdefault(client_name, []).append(port)



# Parse address of various forms ('client:port', (client, port),
# ((client, port),), etc. checking for success or expected error
# exception.
def address_parse(*args):
    # one or two address arguments, then expected client_id, port_id,
    # and expected-error-or-None

    assert len(args) > 3, \
           "internal test program bug: address_parse(%s) <= 3\n" % (args,)

    expected_error = args[ -1]
    port_id        = args[ -2]
    client_id      = args[ -3]
    address_args   = args[:-3]

    global test_count, pass_count, fail_count

    # input of ((a,b),c,d,e) -> ((a,b),) not (a,b)
    if len(address_args) == 1: # and isinstance(address_args[0], tuple):
        address_args = address_args[0]
        is_tuple = False    # for arg_name()
    else:
        is_tuple = True     # for arg_name()

    # format address argument(s) into more readable form
    def arg_name(arg):
        if hasattr(arg, 'client_id'):
            return 'Address(%s)' % str(arg)
        elif is_tuple:
            return str(arg)[1:-1].replace(" ",'')    # strip('()') strips all
        elif isinstance(arg, str):
            if arg.startswith("'"):
                return '"%s"' % arg
            else:
                return "'%s'" % arg
        else:
            return str(arg).replace(" ", '')

    # test successful client.get_address()
    if expected_error is None:
        try:
            addr = tester.get_address(address_args)
        except Exception as e:
            print_stats(sys.stderr)
            sys.stderr.write(  "%s raises unexpected %s\n"
                             % (arg_name(address_args), type(e).__name__))
            raise
    else:
        try:
            addr = tester.get_address(address_args)
        except expected_error:
            test_count += 1
            fail_count += 1
            if opts.verbose:
                sys.stdout.write(  "%s raises %s (as expected)\n"
                                 % (arg_name(address_args),
                                    expected_error.__name__))
            return;
        except Exception as e:
            print_stats(sys.stderr)
            sys.stderr.write(  "%s raises %s (not expected %s)\n"
                             % (arg_name(address_args),
                                type(e).__name__,
                                expected_error.__name__))
            raise
        else:
            print_stats(sys.stderr)
            sys.stdout.write(   "%s -> %d:%d without raising "
                                "expected error %s\n"
                             % (arg_name(address_args),
                                addr.client_id,
                                addr.port_id,
                                expected_error.__name__))
            raise AssertionError

    test_count += 1
    pass_count += 1

    if addr.client_id != client_id or addr.port_id != port_id:
        raise FileNotFoundError(  "%s -> %s, not expected (%d,%d)"
                                % (arg_name(address_args),
                                   addr,
                                   client_id,
                                   port_id  ) )

    if opts.verbose:
        sys.stdout.write(   "%s -> %d:%d"
                         % (arg_name(address_args),
                            addr.client_id,
                            addr.port_id))
        if expected_error is not None:
            sys.stdout.write(" with expected exception: %s\n" % expect_except)
        else:
            sys.stdout.write('\n')

    return addr


# Tests permutations of "numeric-or-named-client:numeric-or-named-port",
# "client:port", "client.port", "'client:port'", (client, port),
# ((client, port)), etc.
def test_variants(client,
                  port,
                  separator,
                  quotes,
                  client_id,
                  port_id,
                  expected_error,
                  has_port_0=True):

    # just client
    just_client_error = None if has_port_0 else FileNotFoundError
    spec = "%s%s%s" % (quotes, client, quotes)
    address_parse(spec,   client_id, 0, just_client_error)
    address_parse(client, client_id, 0, just_client_error)

    # client and port
    spec = "%s%s%s%s%s" % (quotes, client, separator, port, quotes)
    address_parse( spec,                client_id, port_id, expected_error)
    address_parse( client,    port,     client_id, port_id, expected_error)
    address_parse((client,    port),    client_id, port_id, expected_error)
    address_parse( client_id, port,     client_id, port_id, expected_error)
    address_parse((client_id, port),    client_id, port_id, expected_error)
    address_parse( client,    port_id,  client_id, port_id, expected_error)
    address_parse((client,    port_id), client_id, port_id, expected_error)
    address_parse( client_id, port_id,  client_id, port_id, expected_error)
    address_parse((client_id, port_id), client_id, port_id, expected_error)

    if isinstance(client_id, int) and isinstance(port, int) :
        address_parse(Address(client_id, port_id),
                      client_id,
                      port_id,
                      expected_error)



# test all ports of client
def test_addresses(client_name, client_id, ports):
    if opts.verbose:
        sys.stdout.write(  "# --- test_addresses(%s, %s) ---\n"
                         % (client_name, client_id))

    # Not a rigorous test (ports could be explicit with first
    # one not zero) but works for all test cases here where
    # most are implicitly-ordered (so zero is first), and the
    # one that isn't has no port 0 at all much less not
    # as first port.
    has_port_0 = (ports[0].id == 0)

    # permutations of address specifications
    for tests_bits in range(1<<4):
        if (tests_bits & 1): separator = ':'
        else:                separator = '.'

        quotes = ("", "'", '"', None)[(tests_bits >> 1) & 0x3]
        if quotes is None: continue

        no_ports = not(tests_bits << 3)

        for port in ports:
            test_variants(client_name,
                          port.name,
                          separator,
                          quotes,
                          client_id,
                          port.id,
                          None,
                          has_port_0)

        # test that flagged ports can be accessed via substring
        for (port_ndx,port) in enumerate(ports):
            if port.substr:
                # test all 3 character substrings of port name
                for char_ndx in range(0, len(port.name) - 3):
                    substring = port.name[char_ndx:char_ndx+3]
                    test_variants(client_name,
                                  substring,
                                  separator,
                                  quotes,
                                  client_id,
                                  port.id,
                                  None,
                                  has_port_0)



# Test numeric client and port
#
# Note first client created by create_ports() (gets assigned i.d. 128)
# must have port id 0 (explicit or default assigned)
def test_simple():
    if opts.verbose: sys.stdout.write("# --- test_simple() ---\n")

    address_parse(         128,             128, 0, None)
    address_parse(        '128',            128, 0, None)
    address_parse(         128, 0,          128, 0, None)
    address_parse(        '128:0',          128, 0, None)
    address_parse(        (128, 0),         128, 0, None)
    address_parse( Address(128, 0),         128, 0, None)
    address_parse((Address(128, 0),),       128, 0, TypeError)
    address_parse( 128, Address(128, 0),    0,   0, TypeError)
    address_parse((128, Address(128, 0)),   0,   0, TypeError)



# Test of client.get_address() overloads
def test_overloads(client_name, client_id, port_name, port_id):
    if opts.verbose: sys.stdout.write("# --- test_overloads() ---\n")

    overloads = []

    def test(*args):
        overloads.append(address_parse(*(args + (client_id, port_id, None))))

    test( client_id  , port_id  )    # 2 ints
    test((client_id  , port_id  ))   # tuple, same
    test( client_id  , port_name)    # int, str
    test((client_id  , port_name))   # tuple, same
    test( client_name, port_id  )    # str, int
    test((client_name, port_id  ))   # tuple, same
    test( client_name, port_name)    # 2 str
    test((client_name, port_name))   # tuple, same

    test('%d:%d' % (client_id  , port_id  )) # int:int
    test('%d:%s' % (client_id  , port_name)) # int:str
    test('%s:%d' % (client_name, port_id  )) # str:iin
    test('%s:%s' % (client_name, port_name)) # str:str

    overloads.append(tester.get_address(overloads[0]))  # address

    assert(all(addr == overloads[0] for addr in overloads))



def test_bad_arguments():
    if opts.verbose: sys.stdout.write("# --- test_bad_arguments() ---\n")

    address_parse(3.14,                     0, 0, TypeError)
    address_parse([],                       0, 0, TypeError)
    address_parse(tester,                   0, 0, TypeError)

    address_parse((128,),                   0, 0, TypeError)
    address_parse(('explicit',),            0, 0, TypeError)
    address_parse((3.14,),                  0, 0, TypeError)
    address_parse((Address(128,0),),        0, 0, TypeError)

    address_parse(('explicit', None),       0, 0, FileNotFoundError)
    address_parse((3.14, None),             0, 0, TypeError)
    address_parse((Address(128,0), None),   0, 0, TypeError)

    address_parse( 128, 2, 3,               0, 0, TypeError)
    address_parse((128, 2, 3),              0, 0, TypeError)
    address_parse( 128, 2, 3, 4,            0, 0, TypeError)
    address_parse((128, 2, 3, 4),           0, 0, TypeError)

    address_parse( 3.14, 128,               0, 0, TypeError)
    address_parse((3.14, 128),              0, 0, TypeError)
    address_parse( 128, 3.14,               0, 0, TypeError)
    address_parse((128, 3.14),              0, 0, TypeError)

    address_parse( 128, 'explicit',         0, 0, FileNotFoundError)
    address_parse((128, 'explicit'),        0, 0, FileNotFoundError)
    address_parse( 'explicit', 128,         0, 0, FileNotFoundError)
    address_parse(('explicit', 128),        0, 0, FileNotFoundError)

    address_parse( 'explicit', 3.14,        0, 0, TypeError)
    address_parse(('explicit', 3.14),       0, 0, TypeError)
    address_parse( 3.14, 'explicit',        0, 0, TypeError)
    address_parse((3.14, 'explicit'),       0, 0, TypeError)

    address_parse( Address(128, 0),  128,   0, 0, TypeError)
    address_parse((Address(128, 0)), 128,   0, 0, TypeError)

    address_parse( 128, Address(128, 0),    0, 0, TypeError)
    address_parse((128, Address(128, 0)),   0, 0, TypeError)



def test_bad_clients_ports():
    if opts.verbose: sys.stdout.write("# --- test_bad_clients_ports() ---\n")
    for client in (-1, 256, 'bad_client'):
        for port in (0, -1, 256, 'bad_port'):
            test_variants(client,
                          port,
                          ':',
                          '',
                          client,
                          port,
                          FileNotFoundError,
                          has_port_0=False)



def test_good_client_bad_ports(client_name, client_id):
    for port in (-1, 256, 'bad_port'):
        for separator in (':', '.'):
            for quotes in ('', "'", '"'):
                spec = "%s%s%s%s%s" % (quotes,
                                       client_name,
                                       separator,
                                       port,
                                       quotes)
                address_parse(spec,
                              client_name,
                              port,
                              client_id,
                              0,
                              TypeError)
        address_parse( client_name,   port,  client_id, 0, FileNotFoundError)
        address_parse((client_name,   port), client_id, 0, FileNotFoundError)
        address_parse( client_id,     port,  client_id, 0, FileNotFoundError)
        address_parse((client_id,     port), client_id, 0, FileNotFoundError)



if __name__ == '__main__':
    tester     = alsa_midi.SequencerClient("tester"    )   # all tests use this
    sequential = alsa_midi.SequencerClient("sequential")
    prefix     = alsa_midi.SequencerClient("seq"       )
    explicit   = alsa_midi.SequencerClient("explicit"  )

    # First one gets assigned client id 128, must have port
    # with id 0 for test_simple()
    test_id = tester    .get_client_info().client_id
    seqn_id = sequential.get_client_info().client_id
    prfx_id = prefix    .get_client_info().client_id
    expl_id = explicit  .get_client_info().client_id

    # commandline options
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        action="store_true",
                        help="Ouput results of each test (note: thousands)")
    parser.add_argument('-p', '--pause',
                        action="store_true",
                        help="Pause after tests")
    opts = parser.parse_args()

    clients_ports = {}  # have to store ports somewhere else go out of scope
                        # and get deleted on return from create_ports()
    create_ports(tester    , tester_ports    )
    create_ports(sequential, sequential_ports)
    create_ports(prefix    , prefix_ports    )
    create_ports(explicit  , explicit_ports  )

    test_simple()
    test_bad_arguments()
    test_overloads('explicit', expl_id, 'eleven', 11)    # only need to do one
    test_bad_clients_ports()
    test_good_client_bad_ports('explicit', expl_id)  # only need to do one

    test_addresses("tester",     test_id, tester_ports)
    test_addresses("sequential", seqn_id, sequential_ports)
    test_addresses("seq",        prfx_id, prefix_ports) # client,port substrings
    test_addresses("explicit",   expl_id, explicit_ports)
    test_addresses("expl",       expl_id, explicit_ports) # substrings

    if opts.verbose or opts.pause:
        print_stats()

    if opts.pause:
        sys.stdout.write("`aconnect -oil` in separate shell for "
                             "clients+ports, type ^C here to exit\n")
        try:
            while True: pass
        except KeyboardInterrupt:
            sys.stdout.write("exiting\n")

    explicit.close()
    sequential.close()
    tester.close()

    sys.exit(0)
