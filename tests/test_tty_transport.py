from wskr.tty.transport import NoOpTransport


def test_noop_transport_warnings_and_return_value(capsys):
    t = NoOpTransport()
    t.send_image(b"foo")
    result = t.init_image(b"bar")
    out, _ = capsys.readouterr()
    assert "[wskr] Warning" in out
    assert result == -1
