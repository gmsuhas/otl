"""Command line for otl.

    python3 -m otl trace examples/request.log
    python3 -m otl otlp  examples/request.log
    python3 -m otl page  "One request" examples/request.txt > docs/request.html
"""

from __future__ import annotations

import datetime
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
            path, service, day = _otlp_args(rest)
            request = export_request(
                build_trace(_read(path)), service, day=day
            )
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
            "       otl otlp  FILE [SERVICE] [YYYY-MM-DD]\n"
            "       otl page  TITLE FILE [LEAD]"
        )
    return args[0], args[1:]


def _one_file(args):
    if not args or len(args) > 2:
        raise LogError("expected a log file and an optional service name")
    service = args[1] if len(args) == 2 else "otl"
    return args[0], service


def _otlp_args(args):
    if not args or len(args) > 3:
        raise LogError("expected a log file, an optional service, and an optional date")
    service = "otl"
    day = None
    for token in args[1:]:
        if _looks_like_date(token):
            if day is not None:
                raise LogError("expected a single date, YYYY-MM-DD")
            day = _parse_day(token)
        elif service != "otl":
            raise LogError("expected a service name or a date, got %r" % token)
        else:
            service = token
    return args[0], service, day


def _looks_like_date(token):
    return len(token) == 10 and token[4] == "-" and token[7] == "-"


def _parse_day(token):
    try:
        return datetime.date.fromisoformat(token)
    except ValueError:
        raise LogError("expected a date like 2026-11-08, got %r" % token) from None


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
