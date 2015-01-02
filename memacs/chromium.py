#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A Memacs module to org-ify browser history (of Chromium).

It has been developed against the Chromium browser, but should work fine with
Google Chrome, too.  (And possibly can be made to work with Firefox with a few
tweaks).

"""
import os
import logging
import shutil
import sqlite3
import tempfile
import time

from lib.memacs import Memacs
from lib.orgformat import OrgFormat
from lib.orgproperty import OrgProperties


class ChroMemacs(Memacs):
    """A Memacs module to org-ify browser history (of Chromium). """

    name = 'ChroMemacs'

    def _clean_up(self):
        shutil.rmtree(self._workspace)

    def _get_entries_since_last_sync(self):
        return self._get_entries_since(self._get_config_option('last-sync') or None)

    def _get_entries_since(self, last_sync=None):
        self._connection = sqlite3.connect(self._db_path)
        self._cursor = self._connection.cursor()
        self._cursor.row_factory = sqlite3.Row

        if last_sync is None:
            last_sync = 0

        query = (
            # Chrome's epoch is 'Jan 1 00:00:00 UTC 1601'
            '''SELECT url, title, (last_visit_time/1000000)-11644473600 as time
               FROM urls
               WHERE time >= %s
               ORDER BY last_visit_time;''' % last_sync
        )
        entries = self._cursor.execute(query).fetchall()

        self._update_sync_time()
        self._connection.close()

        return entries

    def _main(self):
        """The main entry point, automatically called inside 'handle_main'."""

        logging.info("%s: Started", self.name)
        self._make_db_copy()
        entries = self._get_entries_since_last_sync()
        logging.info("%s: Obtained %d new entries", self.name, len(entries))
        for entry in entries:
            self._write_entry(entry)
        self._clean_up()

    def _make_db_copy(self):
        db_path = self._get_config_option('db')
        if db_path is None:
            db_path = os.path.join(
                '~', '.config', 'chromium', 'Default', 'History'
            )

        db_path = os.path.expanduser(db_path)
        if not os.path.exists(db_path):
            logging.info("%s: Could not find History db", self.name)

        self._workspace = tempfile.mkdtemp()
        self._db_path = os.path.join(self._workspace, 'History')
        shutil.copy(db_path, self._db_path)

        logging.debug("%s: DB copied to %s", self.name, self._db_path)
        return self._db_path

    def _update_sync_time(self):
        # Chrome's epoch is 'Jan 1 00:00:00 UTC 1601'
        timestamp = int(time.time() * 10**6 + 11644473600)
        self._set_config_option('last-sync', timestamp)

    def _write_entry(self, entry):
        timestamp = OrgFormat.datetime(
            time.localtime(entry['time'])
        )

        title = entry['title'].replace('[', '(').replace(']', ')')
        output = OrgFormat.link(entry['url'], title)
        properties = OrgProperties(output)
        self._writer.write_org_subitem(timestamp, output, '', properties)


def main():
    import sys
    argv = sys.argv[1:]

    memacs = ChroMemacs(
        prog_tag='url',
        prog_short_description='Browser History',
        use_config_parser_name='chromium',
        argv=argv
    )

    memacs.handle_main()


if __name__ == "__main__":
    main()
