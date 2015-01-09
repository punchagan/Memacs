#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
from lib.orgformat import OrgFormat
from lib.memacs import Memacs
from lib.orgproperty import OrgProperties

# kindle-utils imports
import log_parser
import book_stats


class KindleMemacs(Memacs):
    def _parser_add_arguments(self):
        """
        overwritten method of class Memacs

        add additional arguments
        """
        Memacs._parser_add_arguments(self)

        self._parser.add_argument('-b', '--book-dir', action='store',
                                dest='book_dir',
                                default='/media/Kindle/documents',
                                help='Path to Kindle userstore documents directory')

        self._parser.add_argument('--state_file', action='store',
                                  dest='state_file',
                                  default=os.path.expanduser('~/.memacs/kindle-utils.state'),
                                  help='Path to file to load/store state from')

        self._parser.add_argument('log_dir', action='store',
                                  help='Path to Kindle logs directory directory')


    def _main(self):
        logs = log_parser.LoadHistory(self._args.state_file)
        if not logs:
            logs = log_parser.KindleLogs()
        logs.ProcessDirectory(self._args.log_dir)
        log_parser.StoreHistory(logs, self._args.state_file)
        books = logs.books
        if len(books) > 0:
            book_data = book_stats.ScanBookMetadata(self._args.book_dir)
        for asin, book in books.items():
            self._log_book(asin, book, book_data)

    def _log_book(self, asin, book, book_data):
        mobi, sidecar = book_data.get(asin, (None, None))
        if mobi is not None:
            title = mobi.title
        else:
            title = asin

        reads = self._get_book_reads(book)
        for start_ts, start, end_ts, end, duration in reads:
            timestamp = OrgFormat.datetimerange(
                time.localtime(start_ts), time.localtime(end_ts)
            )

            properties = OrgProperties(timestamp+title)
            properties.add('ASIN', asin)
            properties.add('TITLE', title)
            properties.add('DURATION', duration)
            properties.add('START_TIME', start_ts)
            properties.add('END_TIME', end_ts)
            properties.add('START_POSITION', start)
            properties.add('END_POSITION', end)

            self._writer.write_org_subitem(
                timestamp=timestamp,
                output=title,
                properties=properties,
            )

    def _get_book_reads(self, book):
        reads = []
        last = None

        for ts, etype, data in sorted(book.events):
            if etype in (book.PICK_UP, book.OPEN):
                start = ts
                startpos = data
            elif etype in (book.CLOSE, book.PUT_DOWN):
                if last in (book.PICK_UP, book.OPEN):
                    duration = ts - start
                    reads.append((start, startpos, ts, data, duration))
            last = etype
        return reads


def main():
    memacs = KindleMemacs(
        prog_tag='kindle:book',
        prog_short_description='Kindle History',
    )

    memacs.handle_main()


if __name__ == "__main__":
    main()
