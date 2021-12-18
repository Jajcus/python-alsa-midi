
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

import pytest


class AlsaPortState:
    client_id: int
    port_id: int
    name: str
    flags: str
    connected_from: List[Tuple[int, int]]
    connected_to: List[Tuple[int, int]]

    def __init__(self, client_id, port_id, name, flags):
        self.client_id = client_id
        self.port_id = port_id
        self.name = name
        self.flags = flags
        self.connected_from = []
        self.connected_to = []

    def __repr__(self):
        return f"<AlsaPortState {self.client_id}:{self.port_id} {self.name!r}>"

    def __str__(self):
        result = f"    Port {self.port_id} {self.name!r} flags={self.flags!r}\n"
        for client_id, port_id in self.connected_from:
            result += f"      connected from {client_id};{port_id}\n"
        for client_id, port_id in self.connected_to:
            result += f"      connected to {client_id};{port_id}\n"
        return result


class AlsaClientState:
    client_id: int
    name: str
    type: str
    ports: Dict[int, AlsaPortState]
    queues: Dict[int, 'AlsaQueueState']

    def __init__(self, client_id, name, client_type):
        self.client_id = client_id
        self.name = name
        self.type = client_type
        self.ports = {}
        self.queues = {}

    def __repr__(self):
        return f"<AlsaClientState {self.client_id} {self.name!r}>"

    def __str__(self):
        result = f"  Client {self.client_id} {self.name!r} type={self.type!r}\n"
        for port in self.ports.values():
            result += str(port)
        return result


PROC_QUEUE_HEADER_RE = re.compile(r'queue\s+(\d+)\s*:\s*\[([^\]]*)\]')
PROC_QUEUE_PARAM_RE = re.compile(r'(\w[\w\s]*\w)\s*:\s*(\S+)')


class AlsaQueueState:
    queue_id: int
    name: str
    client_id: int
    lock_status: str
    queued_time_events: int
    queued_tick_events: int
    timer_state: str
    timer_ppq: int
    current_tempo: int
    current_bpm: int
    current_time: Tuple[int, int]
    current_tick: int

    def __init__(self, lines):
        for line in lines:
            match = PROC_QUEUE_HEADER_RE.match(line)
            if match:
                self.queue_id = int(match.group(1))
                self.name = match.group(2)
                continue
            match = PROC_QUEUE_PARAM_RE.match(line)
            if not match:
                continue
            key = match.group(1)
            value = match.group(2)

            if key == "owned by client":
                self.client_id = int(value)
            elif key == "lock status":
                self.lock_status = value
            elif key == "queued time events":
                self.queued_time_events = int(value)
            elif key == "queued tick events":
                self.queued_tick_events = int(value)
            elif key == "timer state":
                self.timer_state = value
            elif key == "timer PPQ":
                self.timetimer_ppq = int(value)
            elif key == "current tempo":
                self.current_tempo = int(value)
            elif key == "current BPM":
                self.current_bpm = int(value)
            elif key == "current time":
                sec, nsec = value.split(".", 1)
                self.current_time = (int(sec), int(nsec))
            elif key == "current tick":
                self.current_tick = int(value)

    def __repr__(self):
        return f"<AlsaQueueState #{self.queue_id}, owned by {self.client_id}>"

    def __str__(self):
        result = f"  Queue #{self.queue_id} {self.name!r} owned by {self.client_id}\n"
        for key, value in self.__dict__.items():
            if key in ("queue_id", "name", "client_id"):
                continue
            result += f"    {key}: {value}\n"
        return result


PROC_CLIENT_LINE_RE = re.compile(r'Client\s+(\d+)\s*:\s*\"([^"]*)"\s+\[([^\]]*)\]')
PROC_PORT_LINE_RE = re.compile(r'\s+Port\s+(\d+)\s*:\s*\"([^"]*)"\s+\(([^\)]*)\)')
PROC_CONN_TO_LINE_RE = re.compile(r'\s+Connecting To:\s*([\d:, ]+)')
PROC_CONN_FROM_LINE_RE = re.compile(r'\s+Connected From:\s*([\d:, ]+)')


def parse_port_list(string: str) -> List[Tuple[int, int]]:
    port_list = [p.strip() for p in string.split(",")]
    port_list = [p.split(":", 1) for p in port_list]
    port_list = [(int(p[0]), int(p[1])) for p in port_list]
    return port_list


class AlsaSequencerState:
    clients: Dict[int, AlsaClientState]
    ports: Dict[Tuple[int, int], AlsaPortState]
    queues: Dict[int, AlsaQueueState]

    def __init__(self):
        self.clients = {}
        self.ports = {}
        self.queues = {}

    def __str__(self):
        result = "ALSA Sequencer State:\n"
        for client in self.clients.values():
            result += str(client) + "\n"
        for queue in self.queues.values():
            result += str(queue) + "\n"
        return result

    def load(self):
        self.clients = {}
        self.ports = {}
        self.queues = {}

        with open("/proc/asound/seq/clients", "r") as proc_f:
            client = None
            port = None
            for line in proc_f:
                match = PROC_CLIENT_LINE_RE.match(line)
                if match:
                    client = AlsaClientState(int(match.group(1)), match.group(2), match.group(3))
                    self.clients[client.client_id] = client
                    port = None
                    continue
                if not client:
                    continue
                match = PROC_PORT_LINE_RE.match(line)
                if match:
                    port = AlsaPortState(client.client_id, int(match.group(1)),
                                         match.group(2), match.group(3))
                    client.ports[port.port_id] = port
                    self.ports[client.client_id, port.port_id] = port
                    continue
                if not port:
                    continue
                match = PROC_CONN_TO_LINE_RE.match(line)
                if match:
                    port.connected_to = parse_port_list(match.group(1))
                    continue
                match = PROC_CONN_FROM_LINE_RE.match(line)
                if match:
                    port.connected_from = parse_port_list(match.group(1))
                    continue

        with open("/proc/asound/seq/queues", "r") as proc_f:
            queues = []
            queue_lines = []
            for line in proc_f:
                if not line.strip():
                    if queue_lines:
                        queues.append(AlsaQueueState(queue_lines))
                        queue_lines = []
                else:
                    queue_lines.append(line)
            if queue_lines:
                queues.append(AlsaQueueState(queue_lines))
            for queue in queues:
                self.queues[queue.queue_id] = queue
                try:
                    self.clients[queue.client_id].queues[queue.queue_id] = queue
                except KeyError:
                    pass


@pytest.fixture
def alsa_seq_state():
    return AlsaSequencerState()


alsa_seq_present = os.path.exists("/proc/asound/seq/clients")
if not alsa_seq_present:
    try:
        # try triggering snd-seq module load
        with open("/dev/snd/seq", "r"):
            pass
        alsa_seq_present = os.path.exists("/proc/asound/seq/clients")
    except IOError:
        pass


def _check_version(tool):
    def check():
        try:
            subprocess.run([tool, "--version"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            return False
        return True
    return check


tools_present = {}
tools_checks = {
        "aplaymidi": _check_version("aplaymidi"),
        "aseqdump": _check_version("aseqdump"),
        "stdbuf": _check_version("stdbuf"),
        }


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "require_alsa_seq: mark test to require ALSA sequencer in the kernel"
    )
    config.addinivalue_line(
        "markers", "require_no_alsa_seq: mark test to require ALSA sequencer in the kernel"
    )
    config.addinivalue_line(
        "markers", "require_tool: mark test to require a specific tool"
    )


@pytest.fixture(autouse=True)
def skip_if_no_alsa_or_tool(request):
    marker = request.node.get_closest_marker("require_alsa_seq")
    if marker:
        if not alsa_seq_present:
            pytest.skip("ALSA sequencer not available in kernel")
            return
    marker = request.node.get_closest_marker("require_no_alsa_seq")
    if marker:
        if alsa_seq_present:
            pytest.skip("ALSA sequencer available in kernel, but unwanted by this test")
            return
    marker = request.node.get_closest_marker("require_tool")
    if marker:
        tool = marker.args[0]
        if tool in tools_present:
            present = tools_present[tool]
        else:
            present = tools_checks[tool]()
            tools_present[tool] = present
        if not present:
            pytest.skip(f"Tool {tool!r} not available")
            return


@pytest.fixture
@pytest.mark.require_tool("stdbuf")
@pytest.mark.require_tool("aseqdump")
def aseqdump():
    from threading import Thread

    from alsa_midi import Address

    class Aseqdump:
        process: Optional[subprocess.Popen]
        output: List[Tuple[Address, str]]
        port: Address

        def __init__(self, process: subprocess.Popen):
            self.process = process
            self.output = []
            self.read_header()
            self.thread = Thread(name=f"aseqdump-{process.pid}",
                                 target=self.read_output,
                                 daemon=True)
            self.thread.start()

        def read_header(self):
            assert self.process is not None
            assert self.process.stdout is not None
            line = self.process.stdout.readline().decode()
            match = re.search(r" at port (\d+:\d+)\D", line)
            assert match is not None
            self.port = Address(match.group(1))

        def __del__(self):
            if self.process:
                self.close()

        def close(self):
            process = self.process
            if process:
                self.process = None
                process.terminate()

        def read_output(self):
            try:
                while True:
                    process = self.process
                    if process is None:
                        break
                    assert process.stdout is not None
                    line = process.stdout.readline()
                    if not line:
                        break
                    line = line.decode()
                    line = line.strip()
                    addr = line.split(None, 1)[0]
                    if addr == "Source":
                        # header
                        continue
                    try:
                        addr = Address(addr)
                    except ValueError:
                        print(f"Unexpected aseqdump output: {line!r}", file=sys.stderr)
                        continue
                    self.output.append((addr, line))
            except Exception as exc:
                print("read_output thread exception:", exc, file=sys.stderr)
            finally:
                process = self.process
                if process is not None and process.stdout is not None:
                    process.stdout.close()

    process = subprocess.Popen(["stdbuf", "-o", "L", "aseqdump"],
                               bufsize=0,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL,
                               stdin=subprocess.DEVNULL)
    return Aseqdump(process)
