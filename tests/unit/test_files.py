import logging

import pytest
import yaml

from genetic_opt import files
from genetic_opt.files import (
    create_new_folder,
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


@pytest.mark.parametrize(
    "level, logged", [(logging.INFO, True), (logging.WARNING, False)]
)
def test_a_save_reads_the_file_size_only_when_it_is_logged(
    tmp_path, monkeypatch, caplog, set_log_level, level, logged
):
    sizes: list[str] = []
    get_file_size = files.get_file_size

    def counted_get_file_size(file_path):
        sizes.append(file_path)
        return get_file_size(file_path)

    monkeypatch.setattr(files, "get_file_size", counted_get_file_size)
    set_log_level(level)
    save_json(DATA, f"{tmp_path}/data")
    save_bson(DATA, f"{tmp_path}/data")
    save_yaml(DATA, f"{tmp_path}/data")
    saved = [f"{tmp_path}/data.{e}" for e in ("json", "bson", "yml")]
    assert sizes == (saved if logged else [])
    size = get_file_size(saved[0])
    assert [r.message for r in caplog.records][:1] == (
        [f"json saved on: `{saved[0]}`\n\tfile size: {size}"]
        if logged
        else []
    )


def test_save_yaml_keeps_the_order_of_the_keys(tmp_path):
    save_yaml({"b": 1, "a": [1, 2]}, f"{tmp_path}/config")
    with open(f"{tmp_path}/config.yml") as file:
        assert file.read() == "b: 1\na:\n- 1\n- 2\n"


def test_save_yaml_refuses_an_object_that_is_not_plain_data(tmp_path):
    with pytest.raises(yaml.representer.RepresenterError):
        save_yaml({"a": 1, "func": object()}, f"{tmp_path}/config")
    assert get_files_inside_folder(str(tmp_path)) == []


def test_save_yaml_writes_a_repeated_object_in_full(tmp_path):
    repeated = [1, 2]
    save_yaml({"a": repeated, "b": repeated}, f"{tmp_path}/config")
    with open(f"{tmp_path}/config.yml") as file:
        assert file.read() == "a:\n- 1\n- 2\nb:\n- 1\n- 2\n"


def test_save_yaml_with_aliases_writes_a_repeated_object_once(tmp_path):
    repeated = [1, 2]
    save_yaml(
        {"a": repeated, "b": repeated},
        f"{tmp_path}/config",
        ignore_aliases=False,
    )
    with open(f"{tmp_path}/config.yml") as file:
        assert file.read() == "a: &id001\n- 1\n- 2\nb: *id001\n"


def test_save_yaml_leaves_the_yaml_dumper_as_it_was(tmp_path):
    repeated = [1, 2]
    save_yaml({"a": repeated}, f"{tmp_path}/config")
    assert "&id001" in yaml.dump({"a": repeated, "b": repeated})


def test_create_new_folder_never_returns_one_that_exists(tmp_path):
    assert create_new_folder(f"{tmp_path}/a/run/") == f"{tmp_path}/a/run"
    assert create_new_folder(f"{tmp_path}/a/run") == f"{tmp_path}/a/run_2"
    assert create_new_folder(f"{tmp_path}/a/run") == f"{tmp_path}/a/run_3"
    assert get_files_inside_folder(f"{tmp_path}/a/run_3") == []


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
