#!/usr/bin/env python3

from collections import namedtuple

Event = namedtuple("Event", "time bytes")


def tempo_event(bpm):
    midi_tempo = int(1000000 * 60.0 / bpm)
    return Event(0, b"\xff\x51\x03" + midi_tempo.to_bytes(3, byteorder="big"))


def write_file_header(midi_f, format, ntracks, division):
    midi_f.write(b"MThd\x00\x00\x00\x06")
    midi_f.write(format.to_bytes(2, byteorder='big'))
    midi_f.write(ntracks.to_bytes(2, byteorder='big'))
    division = int(division)
    midi_f.write(division.to_bytes(2, byteorder='big'))


def vlq(value):
    """variable-len quantity as bytes"""
    bts = [value & 0x7f]
    while True:
        value = value >> 7
        if not value:
            break
        bts.insert(0, 0x80 | value & 0x7f)
    return bytes(bts)


def write_track(midi_f, events):
    data = []
    for event in events:
        data.append(vlq(event.time))
        data.append(event.bytes)
    data.append(b"\x00\xff\x2f\x00")  # end of track
    data = b"".join(data)
    midi_f.write(b"MTrk")
    midi_f.write(len(data).to_bytes(4, byteorder='big'))
    midi_f.write(data)


def generate_c_major(midi_f):
    div = 96
    write_file_header(midi_f, 0, 1, div)

    events = [tempo_event(1200)]
    for note in [60, 62, 64, 65, 67, 69, 71, 72]:
        events.append(Event(0, bytes([0x90, note, 0x40])))
        events.append(Event(div, bytes([0x80, note, 0x40])))

    write_track(midi_f, events)


if __name__ == "__main__":
    with open("c_major.mid", "wb") as midi_f:
        generate_c_major(midi_f)
