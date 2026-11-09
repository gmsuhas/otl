"""Command line for otl.

    python3 -m otl trace examples/request.log
    python3 -m otl otlp  examples/request.log
    python3 -m otl page  "One request" examples/request.txt > docs/request.html
"""

from __future__ import annotations

import sys

from otl.log import LogError, parse_log
from otl.otlp import dumps, export_request
from otl.page import render_page
from otl.text import render
from otl.trace import build_trace


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        command, rest = _split(args)
        if command == "trace":
            path, service = _one_file(rest)
            sys.stdout.write(render(build_trace(_read(path))))
        elif command == "otlp":
            path, service = _one_file(rest)
            request = export_request(build_trace(_read(path)), service)
            sys.stdout.write(dumps(request))
        elif command == "page":
            title, path, lead = _page_args(rest)
            sys.stdout.write(render_page(title, _read_text(path), lead))
        else:
            raise LogError("unknown command %r" % command)
    except (LogError, OSError) as error:
        sys.stderr.write("otl: %s\n" % error)
        return 1
    return 0


def _split(args):
    if not args or args[0] in ("-h", "--help"):
        raise LogError(
            "usage: otl trace FILE [SERVICE]\n"
            "       otl otlp  FILE [SERVICE]\n"
            "       otl page  TITLE FILE [LEAD]"
        )
    return args[0], args[1:]


def _one_file(args):
    if not args or len(args) > 2:
        raise LogError("expected a log file and an optional service name")
    service = args[1] if len(args) == 2 else "otl"
    return args[0], service


def _page_args(args):
    if len(args) not in (2, 3):
        raise LogError("expected a title, a text file, and an optional lead")
    lead = args[2] if len(args) == 3 else ""
    return args[0], args[1], lead


def _read(path):
    return parse_log(_read_text(path))


def _read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


if __name__ == "__main__":
    sys.exit(main())
