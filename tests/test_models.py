from minutes.models import Entry, EntryStatus, EntryType


def test_entry_roundtrip():
    e = Entry(
        id="a1b2",
        ts="2026-05-27T14:00",
        project="api-migration",
        type=EntryType.ACTION,
        text="Write migration guide",
        due="2026-05-30",
        status=EntryStatus.OPEN,
    )
    assert Entry.from_dict(e.to_dict()) == e


def test_to_dict_omits_none_fields():
    e = Entry(id="x", ts="2026-05-27T09:00", project="p", type=EntryType.NOTE, text="hello")
    d = e.to_dict()
    assert "meeting" not in d
    assert "due" not in d
    assert "status" not in d
    assert "person" not in d
    assert "tags" not in d


def test_to_dict_includes_optional_when_set():
    e = Entry(
        id="x", ts="2026-05-27T09:00", project="p",
        type=EntryType.WAITING, text="approval",
        person="Marco", meeting="team sync",
    )
    d = e.to_dict()
    assert d["person"] == "Marco"
    assert d["meeting"] == "team sync"


def test_make_id_length():
    assert len(Entry.make_id()) == 4


def test_make_id_unique():
    ids = {Entry.make_id() for _ in range(100)}
    assert len(ids) > 90  # allow tiny collision chance


def test_entry_type_values():
    assert EntryType.NOTE.value == "note"
    assert EntryType.ACTION.value == "action"
    assert EntryType.DECISION.value == "decision"
    assert EntryType.WAITING.value == "waiting"


def test_status_roundtrip():
    e = Entry(
        id="z", ts="2026-05-27T10:00", project="p",
        type=EntryType.ACTION, text="do thing",
        status=EntryStatus.DONE,
    )
    d = e.to_dict()
    assert d["status"] == "done"
    assert Entry.from_dict(d).status == EntryStatus.DONE
