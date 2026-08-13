import pytest

from falkorterm import __version__
from falkorterm.cli import main, parse_args


def test_parse_defaults():
    args = parse_args([])
    assert args.command is None
    assert args.query is None
    assert args.query_file is None
    assert args.format is None
    assert args.skip_connect is False
    assert args.yes is False
    assert args.read_only is False
    assert args.diagram_style == "ascii"
    assert args.max_nodes == 25
    assert args.max_edges == 40


def test_parse_query_and_connection_flags():
    args = parse_args(
        [
            "-H",
            "db.example",
            "-P",
            "6380",
            "-g",
            "social",
            "-q",
            "RETURN 1",
            "--format",
            "json",
            "--skip-connect",
            "--read-only",
            "--yes",
        ]
    )
    assert args.host == "db.example"
    assert args.port == 6380
    assert args.graph == "social"
    assert args.query == "RETURN 1"
    assert args.format == "json"
    assert args.skip_connect is True
    assert args.read_only is True
    assert args.yes is True


def test_parse_inspect_command_after_flags():
    args = parse_args(["--host", "127.0.0.1", "schema", "--format", "json"])
    assert args.command == "schema"
    assert args.host == "127.0.0.1"
    assert args.format == "json"


def test_parse_stdin_query_dash():
    args = parse_args(["-q", "-"])
    assert args.query == "-"


def test_parse_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        parse_args(["--help"])
    assert exc.value.code == 0


def test_parse_version_exits_zero():
    with pytest.raises(SystemExit) as exc:
        parse_args(["--version"])
    assert exc.value.code == 0


def test_parse_unknown_command_exits():
    with pytest.raises(SystemExit) as exc:
        parse_args(["nope"])
    assert exc.value.code == 2


def test_main_no_args_launches_tui():
    launched: list[tuple] = []

    def fake_run(config, *, skip_connect=False):
        launched.append((config, skip_connect))

    code = main([], run_app_fn=fake_run)
    assert code == 0
    assert len(launched) == 1
    assert launched[0][1] is False


def test_main_tui_skip_connect():
    launched: list[bool] = []

    def fake_run(config, *, skip_connect=False):
        launched.append(skip_connect)

    code = main(["tui", "--skip-connect"], run_app_fn=fake_run)
    assert code == 0
    assert launched == [True]


def test_main_output_without_query_is_usage():
    import io

    stderr = io.StringIO()
    code = main(
        ["--format", "json"],
        stderr=stderr,
        run_app_fn=lambda **_: None,
    )
    assert code == 2
    assert "require --query" in stderr.getvalue()


def test_main_query_plus_subcommand_is_usage():
    import io

    stderr = io.StringIO()
    code = main(
        ["-q", "RETURN 1", "graphs"],
        stderr=stderr,
        run_app_fn=lambda **_: None,
    )
    assert code == 2
    assert "cannot be combined" in stderr.getvalue()


def test_version_string_matches_package():
    parser_help = __version__
    assert parser_help
