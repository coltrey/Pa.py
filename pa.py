#!/usr/bin/env python
# Pa.py is the Podcast Aggregator in python...
# it basically just auto-downloads all URLs in an <enclosure> element
VERSION = "Pa.py v0.2-beta"

import urllib
import feedparser
import sys
import optparse
import os
import urlparse
import stat

from pprint import pprint

def quote(URL):
    sURL = list(urlparse.urlsplit(URL))
    sURL[2] = urllib.unquote(sURL[2])
    sURL[2] = urllib.quote(sURL[2])
    result = urlparse.urlunsplit(sURL)
    return result

def getFancyDate():
    import datetime
    d = datetime.datetime.today()
    return '/' + ('%04d-%02d-%02d' % (d.year, d.month, d.day,)) + '/'

class ExistsInLog(Exception):
    pass

class fileDescription(object):
    def __init__(self, name, URL, size, options, VERBOSE=False, folderMark='', linkBase=None):
        """folderMark needs to have os.path.sep on both sides"""
        self.URL = URL
        self.size = size
        self.filename = URL.split('/')[-1].split('?')[0]
        self.outputPath = options.baseDir + folderMark + name + os.path.sep
        self.link = linkBase + folderMark + name + os.path.sep + self.filename
        self.logfile = options.baseDir + 'pip.log'
        self.options = options
        self.VERBOSE = VERBOSE

    def __str__(self):
        return ("Name:%s URL:%s Size:%s" % (self.filename, self.URL, self.size,))

    def log(self):
        try:
            self.checkLog()
            l = open(self.logfile, 'a')
            l.write("%s\t%s\n" % (self.filename, self.size))
            if self.VERBOSE:
                print "Logging %s\t%s" % (self.filename, self.size,)
                print "Link is: %s" % self.link
        except ExistsInLog:
            pass

    def checkLog(self):
        try:
            l = open(self.logfile, 'r')
        except IOError, err:
            if err[0] == 2:
                # file does not exist, so return
                return True
            else:
                #otherwise, re-raise the error, since we don't know what to do for real
                raise err

        for name in self.logParse(l):
            if name == self.filename:
                raise ExistsInLog("%s already exists in %s" % (self.filename, self.logfile,))
        return True

    def fetch(self):
        try:
            self.checkLog()
        except ExistsInLog:
            if self.options.VERBOSE:
                sys.stderr.write("%s already exists, skipping...\n" % self.filename)
            return False
        try:
            os.makedirs(self.outputPath)
        except OSError, err:
            # 17 means the directory already exists -- which is fine
            if err[0] != 17:
                raise err
        if self.VERBOSE: print ("Fetching %s" % self.filename)
        try:
            urllib.urlretrieve(quote(self.URL), self.outputPath + self.filename)
            self.log()
            print ("Fetched %s to %s" % (self.filename, self.link))
            return True
        except:
            import traceback;traceback.print_exc()
            return False

    def logParse(self, log):
        """Log file formate: Filename\tFilesize"""
        for line in log:
            yield line.strip().split('\t')[0]

def urlRetreive(URL):
    try:
        return urllib.urlopen(URL).read()
    except KeyboardInterrupt:
        raise
    except:
        sys.stderr.write("Failed to fetch %s\n" % URL)

class Podcast:
    class ItemContainsNothingWanted(Exception):
        pass

    def __init__(self, name, URL, options):
        self.name = name
        self.URL = URL
        self.availableFiles = []
        self.requiredAttributes = 'href', 'length', 'type'
        self.VERBOSE = options.VERBOSE
        self.options = options
        self.mimeTypes = (options.mimeTypes.split(','))

    def parse(self):
        try:
            self.feed = feedparser.parse(self.URL)
        except:
            print "Unexpected error in:", self.name
            import traceback;traceback.print_exc()
        self.entries = self.feed['entries']
        for entry in self.entries:
            if 'enclosures' in entry:
                try:
                    entry = self.validate(entry['enclosures'])
                    self.interpret(entry)
                except self.ItemContainsNothingWanted:
                    continue
        return True

    def validate(self, enclosures):
        # zip is required to sort these by preference.  We should return only one enclosure
        mimes = zip(range(len(self.mimeTypes)),self.mimeTypes)
        initialElements = []
        for enclosure in enclosures:
            hasTheAttrs = True
            for attr in self.requiredAttributes:
                hasTheAttrs = hasTheAttrs and enclosure.has_key(attr)
            if not hasTheAttrs:
                break
            else:
                initialElements.append(enclosure)
        sortedElements = []
        for element in initialElements:
            for type_ in mimes:
                if type_[1] in element['type']:
                    sortedElements.append((type_[0], element))
                else:
                    pass
        if self.VERBOSE:
            if len(sortedElements) == 0:
                for element in initialElements:
                    if element not in sortedElements:
                        sys.stderr.write('%s: Rejected type %s in %s\n' %
                                         (self.name,
                                          element['type'],
                                          element['url'],
                                          ))

        sortedElements.sort()
        try:
            return sortedElements[0][1]
        except IndexError:
            raise self.ItemContainsNothingWanted()


    def interpret(self, element):
        fileURL = element['href']
        fileSize = long(element['length'])
        fileType = element['type']
        fileDesc = fileDescription(self.name, fileURL, fileSize, self.options, VERBOSE=self.VERBOSE, folderMark=getFancyDate(), linkBase=self.options.linkBase)
        self.availableFiles.append(fileDesc)

def getLists(input, options):
    podcastList = []
    for line in input:
        URL, name = line.strip().split()
        if (not options.names) or (name in options.names):
            p = Podcast(name=name, URL=URL, options=options)
            if p.parse():
                podcastList.append(p)
    return podcastList

def parseArgs():
    usage = "usage: %prog [options] args"
    parser = optparse.OptionParser(usage=usage, version=VERSION)
    parser.add_option("-c", "--catchup", dest="catchup",
                      help="catchup-mode (write log, but don't download anything)",
                      action="store_true", default=False)
    parser.add_option("-v", "--verbose", dest="VERBOSE",
                      help="Verbose mode (print out lots of status to stderr)",
                      action="store_true", default=False)
    parser.add_option("-n", "--name", dest="names",
                      help="Only apply the specified action to these names (mulitple names can be specified)",
                      action="append", default=[])
    parser.add_option("-d", "--dir", dest="baseDir",
                      help="base directory where log file, subscription file and all output exist (%prog.log and subscriptions)"
                      )
    parser.add_option("-l", "--link", dest="linkBase", default='https://192.168.1.51/mythweb/data/video/vidcast',
                      help="base URL for mythtv-ish links"
                      )
    parser.add_option("-m", "--mime-types", dest="mimeTypes", default='video',
                      help="list of comma-separated mime-types to retreive, in order of preference -- fetches first match"
                      )

    options, args = parser.parse_args()
    if options.baseDir == None:
        parser.error("-d or --dir is required")
    else:
        import os
        if not options.baseDir.endswith(os.path.sep):
            options.baseDir = options.baseDir + os.path.sep
    return options, args

def main():
    options, args = parseArgs()
    subscription = options.baseDir + 'subscriptions'
    podcastList = getLists(file(subscription), options)
    for podcast in podcastList:
        for fName in podcast.availableFiles:
            if options.catchup:
                fName.log()
            else:
                fName.fetch()

if __name__ == '__main__':
    main()
