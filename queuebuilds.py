#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The MIT License
#
# Copyright 2012 Sony Mobile Communications. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

""" Example of using the Gerrit client class. """

import logging
import optparse
import sys
from threading import Event
import time
import redis
import json

from pygerrit.client import GerritClient
from pygerrit.error import GerritError
from pygerrit.events import ErrorEvent, CommentAddedEvent, ReviewerAddedEvent


def _main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-g', '--gerrit-hostname', dest='hostname',
                      default='review',
                      help='gerrit server hostname (default: %default)')
    parser.add_option('-p', '--port', dest='port',
                      type='int', default=29418,
                      help='port number (default: %default)')
    parser.add_option('-u', '--username', dest='username',
                      help='username')
    parser.add_option('-b', '--blocking', dest='blocking',
                      action='store_true',
                      help='block on event get (default: False)')
    parser.add_option('-t', '--timeout', dest='timeout',
                      default=None, type='int',
                      help='timeout (seconds) for blocking event get '
                           '(default: None)')
    parser.add_option('-v', '--verbose', dest='verbose',
                      action='store_true',
                      help='enable verbose (debug) logging')
    parser.add_option('-i', '--ignore-stream-errors', dest='ignore',
                      action='store_true',
                      help='do not exit when an error event is received')

    (options, _args) = parser.parse_args()
    if options.timeout and not options.blocking:
        parser.error('Can only use --timeout with --blocking')

    level = logging.DEBUG if options.verbose else logging.INFO
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        level=level)

    try:
        gerrit = GerritClient(host=options.hostname,
                              username=options.username,
                              port=options.port)
        logging.info("Connected to Gerrit version [%s]",
                     gerrit.gerrit_version())
        gerrit.start_event_stream()
    except GerritError as err:
        logging.error("Gerrit error: %s", err)
        return 1

    try:
        r = redis.Redis()
    except Exception as err:
        logging.error("Redis error", exc_info=True)
        return 2

    errors = Event()
    try:
        while True:
            event = gerrit.get_event(block=options.blocking,
                                     timeout=options.timeout)
            if event:
                logging.info("Event: %s", event)
                if isinstance(event, ErrorEvent) and not options.ignore:
                    logging.error(event.error)
                    errors.set()
                    break
                elif isinstance(event, CommentAddedEvent):
                    is_reviewed = False
                    if event.change.owner.email != event.author.email:
                        continue

                    for approval in event.approvals:
                        if int(approval.value) == 1 and approval.category == 'Code-Review':
                            is_reviewed = True

                    if is_reviewed:
                        data = {'project': event.change.project,
                                'changeid': event.change.change_id,
                                'subject': event.change.subject,
                                'ref': event.patchset.ref,
                                'revision': event.patchset.revision,
                                'url': event.change.url}
                        r.lpush('omnibuild', json.dumps(data))
                elif isinstance(event, ReviewerAddedEvent):
                    if event.reviewer.email == 'omnibot@omnirom.org':
                        data = {'project': event.change.project,
                                'changeid': event.change.change_id,
                                'ref': event.patchset.ref,
                                'revision': event.patchset.revision,
                                'url': event.change.url}
                        r.lpush('omnibuild', json.dumps(data))
            else:
#                logging.info("No event")
                if not options.blocking:
                    time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Terminated by user")
    except Exception:
        logging.error("Error during processing", exc_info=True)
        errors.set()
    finally:
        logging.warning("Stopping event stream...")
        gerrit.stop_event_stream()

    if errors.isSet():
        logging.error("Exited with error")
        return 1

if __name__ == "__main__":
    sys.exit(_main())

