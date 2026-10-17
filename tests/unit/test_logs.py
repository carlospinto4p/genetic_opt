import logging

from genetic_opt.logs import log_format

# ── log_format Tests ───────────────────────────────────────────────────


def test_log_format_keeps_the_order_of_the_keys():
    assert log_format({"b": 1, "a": [1, 2]}) == "{'b': 1, 'a': [1, 2]}"


def test_log_format_indents_the_lines_it_wraps():
    assert log_format({"b": 1, "a": 2}, width=1) == "{  'b': 1,\n   'a': 2}"


# ── Package Logger Tests ───────────────────────────────────────────────


def test_the_package_leaves_logging_to_the_application():
    logger = logging.getLogger("genetic_opt")
    assert logger.handlers == []
    assert logger.propagate
    assert logger.level == logging.NOTSET
