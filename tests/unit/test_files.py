import pytest

from genetic_opt.files import (
    ensure_file_extension,
    ensure_folder_format,
    get_file_extension,
    get_files_inside_folder,
    load_bson,
    load_json,
    save_bson,
    save_json,
    save_yaml,
)

DATA = {"name": "bag", "values": [1, 2.5, "three"], "nested": {"a": None}}


def test_save_bson_adds_extension_and_roundtrips(tmp_path):
    save_bson(DATA, f"{tmp_path}/folder/data")
    assert load_bson(f"{tmp_path}/folder/data.bson") == DATA


def test_save_json_adds_extension_and_roundtrips(tmp_path):
    save_json(DATA, f"{tmp_path}/folder/data")
    assert load_json(f"{tmp_path}/folder/data.json") == DATA


def test_save_yaml_keeps_the_order_of_the_keys(tmp_path):
    save_yaml({"b": 1, "a": [1, 2]}, f"{tmp_path}/config")
    with open(f"{tmp_path}/config.yml") as file:
        assert file.read() == "b: 1\na:\n- 1\n- 2\n"


def test_get_files_inside_folder_ignores_subfolders(tmp_path):
    save_json(DATA, f"{tmp_path}/b")
    save_json(DATA, f"{tmp_path}/a")
    save_json(DATA, f"{tmp_path}/sub/c")
    assert get_files_inside_folder(f"{tmp_path}/") == ["a.json", "b.json"]
    assert get_files_inside_folder(
        str(tmp_path), return_complete_path=True
    ) == [f"{tmp_path}/a.json", f"{tmp_path}/b.json"]
    assert get_files_inside_folder(str(tmp_path), recursive=True) == [
        "a.json",
        "b.json",
        "sub/c.json",
    ]


def test_get_files_inside_folder_of_empty_folder(tmp_path):
    assert get_files_inside_folder(str(tmp_path)) == []


@pytest.mark.parametrize(
    "file_path, extension",
    [("data.bson", "bson"), ("folder/data.tar.gz", "gz"), ("data", "")],
)
def test_get_file_extension(file_path, extension):
    assert get_file_extension(file_path) == extension


@pytest.mark.parametrize(
    "file_path, extension, expected",
    [
        ("data", "json", "data.json"),
        ("data.json", ".json", "data.json"),
        ("data.yml", "json", "data.yml.json"),
    ],
)
def test_ensure_file_extension(file_path, extension, expected):
    assert ensure_file_extension(file_path, extension) == expected


def test_ensure_folder_format_removes_last_slash():
    assert ensure_folder_format("a/b/") == "a/b"
    assert ensure_folder_format("a/b") == "a/b"
