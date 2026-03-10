from bot.utils.formatter import split_message, MAX_MESSAGE_LENGTH


class TestSplitMessage:
    def test_short_message(self):
        assert split_message("hello") == ["hello"]

    def test_exact_limit(self):
        text = "a" * MAX_MESSAGE_LENGTH
        assert split_message(text) == [text]

    def test_long_message_splits_at_newline(self):
        line = "x" * 100 + "\n"
        text = line * 50  # 5050 chars
        chunks = split_message(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= MAX_MESSAGE_LENGTH

    def test_long_message_no_newlines(self):
        text = "a" * (MAX_MESSAGE_LENGTH + 100)
        chunks = split_message(text)
        assert len(chunks) == 2
        assert len(chunks[0]) == MAX_MESSAGE_LENGTH
