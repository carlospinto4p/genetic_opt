"""Genetic Opt local files submodule."""

from json import dump as dump_json
from json import load as load_json_fun
from logging import INFO
from os import path
from pathlib import Path
from typing import Any

from genetic_opt.functions import format_bytes
from genetic_opt.logs import logger

# `bson`, `matplotlib` and `yaml` are imported inside the functions that
# use them: together they take longer to import than the rest of the
# package, and a run that saves nothing needs none of them.


def _log_saved(kind: str, file_path: str) -> None:
    """
    Log that a file was saved, with its size. The size is read from the
    disk only when the line is going to be logged.
    :param kind: what was saved, as the line names it.
    :param file_path: path of the saved file.
    """
    if logger.isEnabledFor(INFO):
        logger.info(
            f"{kind} saved on: `{file_path}`"
            f"\n\tfile size: {get_file_size(file_path)}"
        )


def create_new_folder(folder: str) -> str:
    """
    Create a folder that did not exist. While one with that name exists,
    `_2`, `_3` and so on is added to the name.
    :param folder: folder path.
    :return: path of the folder created.
    """
    folder_path = Path(folder)
    ensure_folder_exists(folder_path.parent)
    new_folder, attempt = folder_path, 1
    while True:
        try:
            new_folder.mkdir()
        except FileExistsError:
            attempt += 1
            new_folder = folder_path.with_name(
                f"{folder_path.name}_{attempt}"
            )
        else:
            return str(new_folder)


def ensure_file_extension(file_path: str, file_extension: str) -> str:
    """
    Ensure that a file has the extension received.
    :param file_path: path of the target file.
    :param file_extension: extension to set.
    :return: file path with the extension received.
    """
    file_extension = file_extension.removeprefix(".")
    if Path(file_path).suffix != f".{file_extension}":
        file_path = f"{file_path}.{file_extension}"
    return file_path


def ensure_folder_exists(folder: str | Path) -> None:
    """
    Create needed folders to make the received path exists.
    :param folder: folder path.
    :return: None.
    """
    Path(folder).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path: str) -> str | None:
    """
    Get the size of a file, as a formatted string.
    If the file does not exist, will return None.
    """
    if path.exists(file_path):
        return format_bytes(path.getsize(file_path))


def get_files_inside_folder(
    folder: str,
    recursive: bool = False,
    return_complete_path: bool = False,
) -> list[str]:
    """
    Get all the files inside the received folder.
    :param folder: folder path.
    :param recursive: whether to return files inside folders as well.
    :param return_complete_path: whether to append the received folder path to
        the files found inside. Default to False.
    :return: a sorted list of file paths. If `return_complete_path` is False
        (default) will return a sorted list of file names.
    """
    folder_path = Path(folder)
    found = folder_path.rglob("*") if recursive else folder_path.glob("*")
    return sorted(
        str(p if return_complete_path else p.relative_to(folder_path))
        for p in found
        if p.is_file()
    )


def load_bson(bson_path: str) -> Any:
    """
    Load a BSON file.
    :param bson_path: bson file path.
    :return: content of the binary json file.
    """
    import bson

    with open(bson_path, "rb") as file:
        bson_data = file.read()
    return bson.decode(bson_data)


def load_json(json_path: str, **kwargs) -> Any:
    """
    Load a JSON file.
    :param json_path: json file path.
    :param kwargs: Optional arguments to pass to the function `json.load`.
    :return: Loaded JSON object.
    """
    with open(json_path) as file:
        return load_json_fun(file, **kwargs)


def save_bson(data, file_path: str) -> None:
    """Save a .bson file."""
    import bson

    ensure_folder_exists(Path(file_path).parent)
    file_path = ensure_file_extension(file_path, "bson")
    bson_data = bson.BSON.encode(data)
    with open(file_path, "wb") as file:
        file.write(bson_data)
    _log_saved("bson", file_path)


def save_current_figure(
    path: str,
    extension: str = "jpg",
    clear_fig: bool = True,
    close_fig: bool = True,
) -> None:
    """
    Save the current py-plot figure.
    :param path: output path.
    :param extension: image extension to use.
    :param clear_fig: whether to clear the current, saved figure.
        Clear a figure will delete it.
    :param close_fig: whether to close the current, saved figure.
        Close a figure will delete the complete figure window.
        Use this to save memory, not accumulating the plots in memory.
        See https://stackoverflow.com/a/8228808/13376096.
    :return: None.
    """
    import matplotlib.pyplot as plt

    ensure_folder_exists(Path(path).parent)
    file_path = ensure_file_extension(path, extension)
    plt.savefig(file_path, bbox_inches="tight")
    _log_saved("image", file_path)
    if clear_fig:
        plt.clf()
    if close_fig:
        plt.close()


def save_json(data, file_path: str, **kwargs) -> None:
    """
    Save a .json file.
    :param data: Json data to save.
    :param file_path: Json file path to use. Json extension will be added
        if not received.
    :param kwargs: Optional arguments to pass to the function `json.dump`.
    :return: None.
    """
    ensure_folder_exists(Path(file_path).parent)
    file_path = ensure_file_extension(file_path, "json")
    with open(file_path, "w") as file:
        dump_json(data, file, **kwargs)
    _log_saved("json", file_path)


def save_yaml(
    data: dict | list,
    file_path: str,
    encoding: str = "utf8",
    ignore_aliases: bool = True,
) -> None:
    """
    Save a .yaml file that a safe YAML loader reads back.
    :param data: Data to save: dictionaries, lists, strings, numbers,
        booleans, dates and None.
    :param file_path: file path to use. The `yml` extension will be added
        if not received.
    :param encoding: encoding to use. Default to 'utf8'.
    :param ignore_aliases: whether to ignore references for
        duplicated object ids.
    :raises yaml.representer.RepresenterError: when `data` holds any
        other object. No file is written.
    """
    from yaml import SafeDumper
    from yaml import dump as dump_yaml

    class NoAliasSafeDumper(SafeDumper):
        """`SafeDumper` that writes an object met twice in full."""

        def ignore_aliases(self, data: Any) -> bool:
            return True

    ensure_folder_exists(Path(file_path).parent)
    file_path = ensure_file_extension(file_path, "yml")
    text = dump_yaml(
        data,
        Dumper=NoAliasSafeDumper if ignore_aliases else SafeDumper,
        default_flow_style=False,
        sort_keys=False,
    )
    with open(file_path, "w", encoding=encoding) as file:
        file.write(text)
    _log_saved("YAML", file_path)
