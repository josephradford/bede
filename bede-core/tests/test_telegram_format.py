from bede_core.telegram_format import md_to_html, chunk_text


class TestMdToHtml:
    def test_bold(self):
        assert "<b>hello</b>" in md_to_html("**hello**")

    def test_italic(self):
        assert "<i>hello</i>" in md_to_html("*hello*")

    def test_code_inline(self):
        assert "<code>foo</code>" in md_to_html("`foo`")

    def test_code_block(self):
        result = md_to_html("```python\nprint(1)\n```")
        assert "<pre>" in result
        assert "print(1)" in result

    def test_heading_becomes_bold(self):
        assert "<b>Title</b>" in md_to_html("# Title")
        assert "<b>Sub</b>" in md_to_html("## Sub")

    def test_link(self):
        result = md_to_html("[click](https://example.com)")
        assert '<a href="https://example.com">click</a>' in result

    def test_html_entities_escaped(self):
        result = md_to_html("a < b & c > d")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result

    def test_bold_italic(self):
        result = md_to_html("***both***")
        assert "<b><i>both</i></b>" in result


class TestChunkText:
    def test_short_text_single_chunk(self):
        assert chunk_text("hello", 100) == ["hello"]

    def test_splits_at_paragraph(self):
        text = "A" * 50 + "\n\n" + "B" * 50
        chunks = chunk_text(text, 60)
        assert len(chunks) == 2
        assert chunks[0].strip() == "A" * 50
        assert chunks[1].strip() == "B" * 50

    def test_splits_at_newline_if_no_paragraph(self):
        text = "A" * 50 + "\n" + "B" * 50
        chunks = chunk_text(text, 60)
        assert len(chunks) == 2

    def test_splits_at_space_if_no_newline(self):
        text = "word " * 20
        chunks = chunk_text(text, 30)
        assert all(len(c) <= 30 for c in chunks)

    def test_hard_split_if_no_whitespace(self):
        text = "A" * 100
        chunks = chunk_text(text, 40)
        assert len(chunks) == 3
        assert "".join(chunks) == text
