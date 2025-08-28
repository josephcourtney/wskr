from wskr.protocol.noop import NoOpProtocol


def test_noop_protocol_warnings_and_return_value(capsys):
    t = NoOpProtocol()
    t.send_image(b"foo")
    result = t.init_image(b"bar")
    out, _ = capsys.readouterr()
    assert "[wskr] Warning" in out
    assert result == -1


def test_image_protocol_context_manager():
    with NoOpProtocol() as t:
        t.send_image(b"foo")
