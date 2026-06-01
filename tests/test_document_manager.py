from lineup.document.document_manager import DocumentManager

TEMPLATE = "resources/rajtlista.docx"


def test_to_bytes_returns_bytes():
    manager = DocumentManager(TEMPLATE)
    result = manager.to_bytes()
    assert isinstance(result, bytes)


def test_to_bytes_non_empty():
    manager = DocumentManager(TEMPLATE)
    result = manager.to_bytes()
    assert len(result) > 0


def test_to_bytes_is_valid_docx():
    manager = DocumentManager(TEMPLATE)
    result = manager.to_bytes()
    assert result[:2] == b"PK"


def test_save_creates_file(tmp_path):
    manager = DocumentManager(TEMPLATE)
    output = tmp_path / "output.docx"
    manager.save(str(output))
    assert output.exists()


def test_update_paragraph_text_out_of_range(capsys):
    manager = DocumentManager(TEMPLATE)
    manager.update_paragraph_text(9999, "text")
    assert "out of range" in capsys.readouterr().out


def test_add_run_out_of_range(capsys):
    manager = DocumentManager(TEMPLATE)
    manager.add_run(9999, "text")
    assert "out of range" in capsys.readouterr().out


def test_underline_run_out_of_range(capsys):
    manager = DocumentManager(TEMPLATE)
    manager.underline_run(9999, "text")
    assert "out of range" in capsys.readouterr().out


def test_make_run_bold_out_of_range(capsys):
    manager = DocumentManager(TEMPLATE)
    manager.make_run_bold(9999, "text")
    assert "out of range" in capsys.readouterr().out


def test_get_table_cell_row_out_of_range(capsys):
    manager = DocumentManager(TEMPLATE)
    manager.get_table_cell(table_index=0, row=9999, column=0)
    assert "out of range" in capsys.readouterr().out


def test_get_table_cell_table_out_of_range(capsys):
    manager = DocumentManager(TEMPLATE)
    manager.get_table_cell(table_index=9999)
    assert "out of range" in capsys.readouterr().out
