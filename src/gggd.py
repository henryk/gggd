#!/usr/bin/env python2.7
# encoding: utf-8
'''
gggd -- Get Google Groups Data

gggd is a tool to download raw mbox content for all posts in a Google Group

@author:     Henryk Plötz <henryk@ploetzli.ch>

@copyright:  2014 Henryk Plötz. All rights reserved.

@license:    GPL-2

@contact:    henryk@ploetzli.ch
@deffield    updated: Updated
'''

import sys
import os

from os.path import expanduser

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import subprocess
import xml.etree.ElementTree as ElementTree

__all__ = []
__version__ = 0.1
__date__ = '2014-11-03'
__updated__ = '2014-11-03'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

class LynxFetcher(object):
    def __init__(self, lynx_cfg=None):
        self.lynx_cfg = lynx_cfg
    
    def fetch(self, url, list_only=False, source=False):
        args = ["lynx", "-dump"]
        if list_only:
            args.append("-listonly")
        if source:
            args.append("-source")
        if self.lynx_cfg:
            args.append( "-cfg=" + self.lynx_cfg )
        args.append(url)
        return subprocess.check_output(args)

class GroupInformation(object):
    def __init__(self, fetcher, group_name):
        self.fetcher = fetcher
        self.group_name = group_name
        self.topics = {}
    
    def fetch(self, topic_page_limit=None):
        self.fetch_topics(topic_page_limit)
        self.fetch_messages()
        self.fetch_content()
    
    def fetch_topics(self, page_limit=None):
        global verbose
        if verbose: print "Fetching topics ..."
        next_page = "https://groups.google.com/forum/?_escaped_fragment_=forum/%s" % self.group_name
        while next_page and page_limit is None or page_limit > 0:
            if verbose: print "Fetching %s" % next_page
            data = self.fetcher.fetch(next_page, list_only=True)
            next_page = self.parse_topics(data)
            if page_limit is not None:
                page_limit = page_limit - 1
    
    def parse_topics(self, data):
        global verbose
        next_page = None
        for line in data.splitlines():
            parts = line.split()
            if len(parts) > 1 and parts[1].startswith("https://groups.google.com/d/topic/%s" % self.group_name):
                t = parts[1].split("/")[-1]
                self.topics[t] = {}
                if verbose: print "Discovered %s" % parts[1]
            elif len(parts) > 1 and parts[1].startswith("https://groups.google.com/forum/?_escaped_fragment_=forum/"):
                next_page = parts[1]
                if verbose: print "Next page is %s" % parts[1]
        return next_page
    
    def fetch_messages(self):
        global verbose
        if verbose: print "Fetching messages ..."
        for topic in self.topics.keys():
            self.fetch_messages_topic(topic)
    
    def fetch_messages_topic(self, topic):
        global verbose
        next_page = "https://groups.google.com/forum/?_escaped_fragment_=topic/%s/%s" % (self.group_name, topic)
        if verbose: print "Fetching %s" % next_page
        data = self.fetcher.fetch(next_page, list_only=True)
        for line in data.splitlines():
            parts = line.split()
            if len(parts) > 1 and parts[1].startswith("https://groups.google.com/d/msg/%s/%s" % (self.group_name, topic)):
                m = parts[1].split("/")[-1]
                self.topics[topic][m] = None
                if verbose: print "Discovered %s" % parts[1]
    
    def fetch_content(self):
        global verbose
        for topic in self.topics.keys():
            if verbose: print "Retrieving message contents for topic %s ..." % topic
            for message in self.topics[topic].keys():
                message_url = "https://groups.google.com/forum/message/raw?msg=%s/%s/%s" % (self.group_name, topic, message)
                if self.topics[topic][message] is None:
                    if verbose: print "Fetching %s" % message_url
                    data = self.fetcher.fetch(message_url, source=True)
                    self.topics[topic][message] = data
                else:
                    if verbose: "Skipping %s " % message_url
    
    def write_tree(self):
        global verbose
        for topic in self.topics.keys():
            if verbose: print "Writing message contents for topic %s ..." % topic
            for message in self.topics[topic].keys():
                if self.topics[topic][message]:
                    file_name = os.path.join(self.group_name, topic, message)
                    if not os.path.exists(file_name):
                        if verbose: print "Writing message %s" % file_name
                        dir_name = os.path.join(self.group_name, topic)
                        if not os.path.exists(dir_name):
                            os.makedirs(dir_name)
                        with open(file_name, "w") as fp:
                            fp.write(self.topics[topic][message])
                    else:
                        if verbose: print "Skipping %s, exists" % file_name
    
    def read_tree(self, read_contents = True):
        for topic in os.listdir(self.group_name):
            self.topics[topic] = {}
            for message in os.listdir( os.path.join(self.group_name, topic) ):
                if read_contents:
                    self.topics[topic][message] = open( os.path.join(self.group_name, topic, message, "r") ).read()
                else:
                    self.topics[topic][message] = None
    
    def fetch_update(self, update_count, replace_information=False):
        global verbose
        if verbose: print "Retrieving update RSS ..."
        rss_url = "https://groups.google.com/forum/feed/%s/msgs/rss.xml?num=%i" % (self.group_name, update_count)
        data = self.fetcher.fetch(rss_url, source=True)
        
        root = ElementTree.fromstring(data)
        
        topics = {}
        
        nodes = root.findall(".//item/link")
        for node in nodes:
            url = node.text
            if url.startswith("https://groups.google.com/d/msg/%s" % self.group_name):
                topic, message = url.split("/")[-2:]
                if verbose: print "Discovered %s, %s" % (topic, message)
                
                if not topic in self.topics:
                    if verbose: print "Topic %s is new" % topic
                    self.topics[topic] = {}
                    topics[topic] = {}
                
                if not message in self.topics[topic]:
                    if verbose: print "Message %s is new" % message
                    self.topics[topic][message] = None
                    
                    if not topic in topics: topics[topic] = {}
                    topics[topic][message] = None
        
        if replace_information:
            self.topics = topics
        
        self.fetch_content()



class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''
    global verbose 
    
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by Henryk Plötz <henryk@ploetzli.ch> on %s.
  Copyright 2014 Henryk Plötz. All rights reserved.

  Licensed under the GNU General Public License 2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        parser.add_argument("-t", "--topic-page-limit", dest="topic_page_limit", help="Number of topic overview pages to process, usually at 20 topics per page", default=None, type=int)
        parser.add_argument("-c", "--lynx-cfg", dest="lynx_cfg", help="Lynx configuration file [default: %(default)s]", default=expanduser("~/.lynxrc"))
        parser.add_argument("-u", "--update", help="Don't spider, but update from RSS of last messages", action="store_true")
        parser.add_argument("-U", "--update-count", help="Number of messages to request in RSS for --update mode, default: 50", default=None, type=int)
        parser.add_argument(dest="group", help="Name of the Google Group to fetch", metavar="group")

        # Process arguments
        args = parser.parse_args()
        if args.update_count is None:
            args.update_count = 50
        else:
            args.update = True
        
        group = args.group
        verbose = args.verbose

        if verbose > 0:
            print("Verbose mode on")

        fetcher = LynxFetcher(args.lynx_cfg)
        
        group_information = GroupInformation(fetcher, group)
        
        if args.update:
            group_information.read_tree(read_contents=False)
            group_information.fetch_update(args.update_count, replace_information=True)
        else:
            group_information.fetch(args.topic_page_limit)
        
        group_information.write_tree()
        
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG or TESTRUN:
            raise
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'gggd_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())
