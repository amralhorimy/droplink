from app.modules.files import domain as d


def test_happy_path():
    assert d.can_transition(d.PENDING, d.UPLOADED)
    assert d.can_transition(d.UPLOADED, d.PROCESSING)
    assert d.can_transition(d.PROCESSING, d.READY)


def test_no_shortcuts_and_no_way_back():
    assert not d.can_transition(d.PENDING, d.READY)
    assert not d.can_transition(d.READY, d.PROCESSING)
    assert not d.can_transition(d.DELETED, d.READY)


def test_everything_alive_can_be_deleted():
    for state in (d.PENDING, d.UPLOADED, d.PROCESSING, d.READY, d.FAILED):
        assert d.can_transition(state, d.DELETED)


def test_allowed_from_is_derived_from_the_machine():
    assert d.allowed_from(d.UPLOADED) == {d.PENDING}
    assert d.allowed_from(d.READY) == {d.PROCESSING}
    assert d.PROCESSING in d.allowed_from(d.PROCESSING)  # retry
