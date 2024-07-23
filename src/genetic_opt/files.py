
import bson

from cpinto.files import ensure_file_extension, ensure_folder_exists, \
    get_container_folder, get_file_size, normalize_path

from genetic_opt.logs import logger


def load_bson(bson_path: str):
    """
    Load a BSON file.
    :param bson_path: bson file path.
    :return: content of the binary json file.
    """
    with open(bson_path, 'rb') as file:
        bson_data = file.read()
    return bson.BSON.decode(bson_data)


def save_bson(data, file_path: str) -> None:
    """ Save a .bson file. """
    ensure_folder_exists(get_container_folder(file_path))
    file_path = ensure_file_extension(file_path, 'bson')
    bson_data = bson.BSON.encode(data)
    with open(file_path, 'wb') as file:
        file.write(bson_data)
    logger.info(f'json saved on: `{normalize_path(file_path)}`'
                f'\n\tfile size: {get_file_size(file_path)}')
