'''    
    pypt-offline  -- An offline package manager for Debian and its derivatives
    Copyright (C) 2007  Ritesh Raj Sarraf

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import sys
import shutil
import platform
import string
import urllib2
import Queue
import threading
import optparse
import socket
import tempfile

import zipfile

# On Debian, python-debianbts package provides this library
DebianBTS = True
try:
    import debianbts
except ImportError:
    DebianBTS = False

import pypt_magic

guiBool = True
try:
    from qt import *
    from pyptofflinegui import pyptofflineguiForm
except ImportError:
    guiBool = False
    
#INFO: Check if python-apt is installed
PythonApt = True
try:
    import apt
    import apt_pkg
except ImportError:
    PythonApt = False
    
try:
    sys.path.append(os.path.dirname(__file__) + "/MyPythonLib")
    import MyPythonLib
except ImportError:
    sys.stderr.write("MyPythonLib library not found. Check installation.\n")
    sys.exit(1)

#INFO: Set the default timeout to 15 seconds for the packages that are being downloaded.
socket.setdefaulttimeout(30)

# How many times should we retry on socket timeouts
SOCKET_TIMEOUT_RETRY = 5

'''This is the core module. It does the main job of downloading packages/update packages,\nfiguring out if the packages are in the local cache, handling exceptions and many more stuff'''


version = "0.7.0"
copyright = "(C) 2005 - 2007 Ritesh Raj Sarraf - RESEARCHUT (http://www.researchut.com/)"
terminal_license = "This program comes with ABSOLUTELY NO WARRANTY.\n\
This is free software, and you are welcome to redistribute it under certain conditions.\n\n\n"
        
errlist = []
supported_platforms = ["Linux", "GNU/kFreeBSD", "GNU"]
apt_update_target_path = '/var/lib/apt/lists/'
apt_package_target_path = '/var/cache/apt/archives/'

pypt_bug_file_format = "__pypt__bug__report"
IgnoredBugTypes = ["Resolved bugs", "Normal bugs", "Minor bugs", "Wishlist items", "FIXED"]


#These are spaces which will overwrite the progressbar left mess
LINE_OVERWRITE_SMALL = " " * 10
LINE_OVERWRITE_MID = " " * 30
LINE_OVERWRITE_FULL = " " * 60

       
class FetchBugReports(MyPythonLib.Archiver):
    def __init__(self, pypt_bug_file_format, IgnoredBugTypes, ArchiveFile=None, lock=False):
        
        self.bugsList = []
        self.IgnoredBugTypes = IgnoredBugTypes
        self.lock = lock
        self.pypt_bug = pypt_bug_file_format
        
        if self.lock:
            MyPythonLib.Archiver.__init__(self, lock)
            self.ArchiveFile = ArchiveFile
        
    def FetchBugsDebian(self, PackageName, Filename=None):
        '''
        0 => False
        1 => No Bug Reports
        2 => True
        '''
        
        if Filename != None:
            try:
                file_handle = open(Filename, 'a')
            except IOError:
                sys.exit(1)
                
        try:
            (num_of_bugs, header, self.bugs_list) = debianbts.get_reports(PackageName)
        except socket.timeout:
            return 0
        
        if num_of_bugs:
            atleast_one_bug_report_downloaded = False
            for x in self.bugs_list:
                (sub_bugs_header, sub_bugs_list) = x
                
                #INFO: We filter all the IgnoredBugTypes that we think aren't necessary.
                # We don't download those low priority bug reports
                for BugType in self.IgnoredBugTypes:
                    if BugType in sub_bugs_header:
                        bug_flag = 0
                        break
                    bug_flag = 1
                        
                if bug_flag:
                    
                    for x in sub_bugs_list:
                        break_bugs = x.split(':')
                        bug_num = string.lstrip(break_bugs[0], '#')
                        try:
                            data = debianbts.get_report(bug_num, followups=True)
                        except socket.timeout:
                            return False
                        if Filename == None:
                            self.fileName = PackageName + "." + bug_num + "." + self.pypt_bug
                            file_handle = open(self.fileName, 'w')
                        else:
                            file_handle = open(Filename, 'a')
                            
                        file_handle.write(data[0] + "\n\n")
                        for x in data[1]:
                            file_handle.write(x)
                            file_handle.write("\n")
                        
                        file_handle.write("\n" * 3)
                        file_handle.flush()
                        file_handle.close()
                        
                        #We're adding to an archive file here.
                        if self.lock:
                            self.AddToArchive(self.ArchiveFile)
                        
                        atleast_one_bug_report_downloaded = True
            if atleast_one_bug_report_downloaded:
                return 2
            else:
                return 1
        else:
            #FIXME: When no bug reports are there, i.e. bug count is 0, we hit here
            # We shouldn't be returning False
            return 1
    
    def AddToArchive(self, ArchiveFile):
        if self.compress_the_file(self.ArchiveFile, self.fileName):
            os.unlink(self.fileName)
            return True
        
        
def files(root): 
    for path, folders, files in os.walk(root): 
        for file in files: 
            yield path, file 
    
    
def find_first_match(cache_dir=None, filename=None):
    '''Return the full path of the filename if a match is found
    Else Return False'''

    # Do the sanity check first
    #if cache_dir is None or filename is None or os.path.isdir(cache_dir) is False:
    if cache_dir is None:
        return False
    elif filename is None:
        return False
    elif os.path.isdir(cache_dir) is False:
        return False
    else:
        for path, file in files(cache_dir): 
            if file == filename:
                return os.path.join(path, file)
        return False
        
        
class DownloadFromWeb(MyPythonLib.ProgressBar):
    '''
    Class for DownloadFromWeb
    
    This class also inherits progressbar functionalities from
    parent class, ProgressBar
    '''
    
    def __init__(self, width):
        '''
        width = Progress Bar width
        '''
        MyPythonLib.ProgressBar.__init__(self, width=width)
    
    def download_from_web(self, url, file, download_dir):
        '''
        url = url to fetch
        file = file to save to
        donwload_dir = download path
        '''
           
        try:
            block_size = 4096
            i = 0
            counter = 0
            
            os.chdir(download_dir)
            temp = urllib2.urlopen(url)
            headers = temp.info()
            size = int(headers['Content-Length'])
            data = open(file,'wb')
            
            #INFO: Add the download thread into the Global ProgressBar Thread
            self.addItem(size)
     
            socket_counter = 0
            while i < size:
                socket_timeout = None
                try:
                    data.write (temp.read(block_size))
                except socket.timeout, timeout:
                    socket_timeout = True
                    socket_counter += 1
                except socket.error, error:
                    socket_timeout = True
                    socket_counter += 1
                if socket_counter == SOCKET_TIMEOUT_RETRY:
                    errfunc(101010, "Max timeout retry count reached. Discontinuing download.\n", file)
                    return False
                    #break
                if socket_timeout is True:
                    errfunc(10054, "Socket Timeout. Retry - %d\n" % (socket_counter) , file)
                    continue
                
                increment = min(block_size, size - i)
                i += block_size
                counter += 1
                self.updateValue(increment)
                
            self.completed()
            data.close()
            temp.close()
            
            return True
            
        #FIXME: Find out optimal fix for this exception handling
        except OSError, (errno, strerror):
            errfunc(errno, strerror, download_dir)
            
        except urllib2.HTTPError, errstring:
            errfunc(errstring.code, errstring.msg, file)
            
        except urllib2.URLError, errstring:
            # URLErrors shouldn't be ignored, hence program termination
            if errstring.reason.args[0] == 10060:
                errfunc(errstring.reason.args[0], errstring.reason, url)
        
        except IOError, e:
            if hasattr(e, 'reason'):
                log.err("%s\n" % (e.reason))
            if hasattr(e, 'code') and hasattr(e, 'reason'):
                errfunc(e.code, e.reason, file)
                
        except socket.timeout:
            errfunc(10054, "Socket timeout.\n", file)


def copy_first_match(cache_dir, filename, dest_dir, checksum): # aka new_walk_tree_copy() 
    '''Walks into "reposiotry" looking for "filename".
    If found, copies it to "dest_dir" but first verifies their md5 "checksum".'''
    
    # If the repository is not given, we'll return None because the user wants to download
    # it from the web
    # There's no need to walk also because the user knows that he doesn't have any cache_dir
    # Earlier implementation of having a default dir (os.curdir()) hit performance badly because
    # at times it would start the walk from "C:\" or "/"
    if cache_dir is None:
        return False
    
    for path, file in files(cache_dir): 
        if file == filename:
            #INFO: md5check is compulsory here
            # There's no point in checking for the disable-md5 option because
            # copying a damaged file is of no use
            if pypt_md5_check.CheckHashDigest(file, checksum, path) == True:
                try:
                    shutil.copy(os.path.join(path, file), dest_dir)
                except shutil.Error:
                    log.verbose("%s already available in dest_dir. Skipping copy!!!\n" % (file))
                return True
    return False


def stripper(item):
    '''Strips extra characters from "item".
    Breaks "item" into:
    url - The URL
    file - The actual package file
    size - The file size
    md5_text - The md5 checksum test
    and returns them.'''
    
    #INFO: This is obsolete
    #lSplitData = each_single_item.split(' ') # Split on the basis of ' ' i.e. space
    # We initialize the variables "sUrl" and "sFile" here.
    # We also strip the single quote character "'" to get the real data
    #sUrl = string.rstrip(string.lstrip(''.join(lSplitData[0]), chars="'"), chars="'")
    #sFile = string.rstrip(string.lstrip(''.join(lSplitData[1]), chars="'"), chars="'")
            
    item = item.split(' ')
    url = string.rstrip(string.lstrip(''.join(item[0]), chars="'"), chars="'")
    file = string.rstrip(string.lstrip(''.join(item[1]), chars="'"), chars="'")
    size = int(string.rstrip(string.lstrip(''.join(item[2]), chars = "'"), chars="'"))
    #INFO: md5 ends up having '\n' with it.
    # That needs to be stripped too.
    md5_text = string.rstrip(string.lstrip(''.join(item[3]), chars = "'"), chars = "'")
    md5_text = string.rstrip(md5_text, chars = "\n")
    
    return url, file, size, md5_text


def errfunc(errno, errormsg, filename):
    '''
    We use errfunc to handler errors.
    There are some error codes (-3 and 13 as of now)
    which are temporary codes, they happen when there
    is a temporary resolution failure, for example.
    For such situations, we can't abort because the
    uri file might have other hosts also, which might
    be well accessible.
    This function does the job of behaving accordingly
    as per the error codes.
    '''
    error_codes = [-3, 13, 504, 404, 10060, 104, 101010]
    # 104, 'Connection reset by peer'
    # 504 is for gateway timeout
    # 404 is for URL error. Page not found.
    # 10060 is for Operation Time out. There can be multiple reasons for this timeout
    # 101010 is for socket max retry count
    # 10054 is for Socket Timeout. Socket Timeout are seen during network congestion
    
    #TODO: Find out what these error codes are for
    # and better document them the next time you find it out.
    # 13 is for "Permission Denied" when you don't have privileges to access the destination 
    if errno in error_codes:
        log.err("%s - %s - %s.%s\n" % (filename, errno, errormsg, LINE_OVERWRITE_MID))
        log.verbose("Will still try with other package uris\n")
        pass
    
    elif errno == 10054:
        log.verbose("%s - %s - %s.%s\n" % (filename, errno, errormsg, LINE_OVERWRITE_SMALL) )
        pass
    
    elif errno == 407 or errno == 2:
        # These, I believe are from OSError/IOError exception.
        # I'll document it as soon as I confirm it.
        log.err("%s\n" % (errormsg))
        sys.exit(errno)
        
    elif errno == 1:
        log.err(errormsg)
        log.err("Explicit program termination %s\n" % (errno))
        sys.exit(errno)
        
    else:
        log.err("I don't understand this error code %s\n" % (errno))
        sys.exit(errno)
        
        
def get_pager_cmd(pager_cmd = None):
    
    if os.name == 'posix':
        default_pager_cmd = 'less -r'
    elif os.name in ['nt', 'dos']:
        default_pager_cmd = 'type'
        
    if pager_cmd is None:
        try:
            pager_cmd = os.environ['PAGER']
        except:
            pager_cmd = default_pager_cmd
    
    return pager_cmd


class PagerCmd:
    """ Tries to automatically detect and set the pager on the running OS"""
    
    def __init__(self, pager_cmd = None):
        if os.name == 'posix':
            self.default_pager_cmd = 'less -r'
        elif os.name in ['nt', 'dos']:
            self.default_pager_cmd = 'type'
            
        if pager_cmd is None:
            try:
                self.pager_cmd = os.environ['PAGER']
            except:
                self.pager_cmd = self.default_pager_cmd
                
    def send_to_pager(self, String = None):
        """Writes the String to the pager"""
        if String is None:
            return False
        else:
            try:
                retval = None # None is correct. On success, None is returned
                pager = os.popen(self.pager_cmd, 'w')
                pager.write(String)
                #pager.close()
                retval = pager.close()
            except IOError,msg:  # broken pipe when user quits
                if msg.args == (32,'Broken pipe'):
                    retval = None
                else:
                    retval = 1
            except OSError:
                retval = 1
        return retval
            

def fetcher(ArgumentOptions, arg_type = None):
    '''
    uri - The uri data whill will contain the information
    path - The path (if any) where the download needs to be done
    cache - The cache (if any) where we should check before downloading from the net
    arg_type - arg_type is basically used to identify wether it's a update download or upgrade download
    '''
    
    cache_dir = ArgumentOptions.cache_dir
    if cache_dir is not None:
        if os.path.isdir(cache_dir) is False:
            log.verbose("WARNING: cache dir is incorrect. Did you give the full path ?\n")
    
    class FetcherClass(DownloadFromWeb, MyPythonLib.Archiver, MyPythonLib.Checksum):
        def __init__(self, width, lock):
            DownloadFromWeb.__init__(self, width=width)
            #ProgressBar.__init__(self, width)
            #self.width = width
            MyPythonLib.Archiver.__init__(self, lock=lock)
            #self.lock = lock
            
    #global FetcherInstance
    FetcherInstance = FetcherClass(width=30, lock=True)
    #INFO: For the Progress Bar
    #progbar = ProgressBar(width = 30)
    
    if ArgumentOptions.download_dir is None:
        if os.access("pypt-downloads", os.W_OK) is True:
            download_path = os.path.abspath("pypt-downloads")
        else:
            try:
                os.umask(0002)
                os.mkdir("pypt-downloads")
                download_path = os.path.abspath("pypt-downloads")
            except:
                log.err("I couldn't create a directory")
                errfunc(1, '')
    else:
        if os.access(ArgumentOptions.download_dir, os.W_OK) is True:
            download_path = os.path.abspath(ArgumentOptions.download_dir)
        else:
            try:
                os.umask(0002)
                os.mkdir(ArgumentOptions.download_dir)
                download_path = os.path.abspath(ArgumentOptions.download_dir)
            except:
                log.err("I couldn't create a directory")
                errfunc(1, '')
            
    zip_update_file = os.path.join(os.path.abspath(download_path), ArgumentOptions.zip_update_file) 
    zip_upgrade_file = os.path.join(os.path.abspath(download_path), ArgumentOptions.zip_upgrade_file) 
    
    if ArgumentOptions.deb_bugs:
        if DebianBTS is True:
            if ArgumentOptions.zip_it:
                FetchBugReportsDebian = FetchBugReports(pypt_bug_file_format, IgnoredBugTypes, zip_upgrade_file, lock=True)
            else:
                FetchBugReportsDebian = FetchBugReports(pypt_bug_file_format, IgnoredBugTypes)
        else:
            log.err("Couldn't find debianbts module.\n Cannot fetch Bug Reports.\n")
            
    FetchData = {}
    if ArgumentOptions.fetch_update:
        try:
            raw_data_list = open(ArgumentOptions.fetch_update, 'r').readlines()
        except IOError, (errno, strerror):
            log.err("%s %s\n" % (errno, strerror))
            errfunc(errno, '')
        
        FetchData['Update'] = []
        for item in raw_data_list:
            FetchData['Update'].append(item)
            
        if os.access(os.path.join(download_path, ArgumentOptions.zip_update_file), os.F_OK):
            log.err("%s already present.\nRemove it first.\n" % (zip_update_file) )
            sys.exit(1)
        
            
    if ArgumentOptions.fetch_upgrade:
        try:
            raw_data_list = open(ArgumentOptions.fetch_upgrade, 'r').readlines()
        except IOError, (errno, strerror):
            log.err("%s %s\n" % (errno, strerror))
            errfunc(errno, '')
        
        FetchData['Upgrade'] = []
        for item in raw_data_list:
            FetchData['Upgrade'].append(item)
            
        if os.access(os.path.join(download_path, ArgumentOptions.zip_upgrade_file), os.F_OK):
            log.err("%s already present.\nRemove it first.\n" % (zip_upgrade_file) )
            sys.exit(1)
            
    del raw_data_list
        
        
    #INFO: Mac OS is having issues with Python Threading.
    # Use the conventional model for Mac OS
    if sys.platform == 'darwin':
        log.verbose("Running on Mac OS! pypt-offline doesn't have proper support for Threads on Mac OS X.\n")
        log.verbose("Running in the conventional non-threaded way.\n")
        
        for key in FetchData.keys():
            for item in FetchData.get(key):
                
                (url, file, download_size, checksum) = stripper(each_single_item)
                
                if key == 'Update':
                    temp_file = file.split("_")
                    PackageName = temp_file[0]
                    PackageName += " - " + temp_file[len(temp_file) - 1]
                    del temp_file
                    
                    log.msg("Downloading %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) ) 
                    if FetcherInstance.download_from_web(url, file, download_path) != True:
                        errlist.append(file)
                    else:
                        log.success("%s done.%s\n" % (PackageName, LINE_OVERWRITE_FULL) )
                        if ArgumentOptions.zip_it:
                            if FetcherInstance.compress_the_file(zip_update_file, file) != True:
                                log.verbose("%s added to archive %s.\n" % (file, zip_update_file) )
                                os.unlink(os.path.join(download_path, file) ) # Remove it because we don't need the file once it is zipped.
                        pass
                                        
                elif key == 'Upgrade':
                    PackageName = file.split("_")[0]
                    if cache_dir is None:
                        log.msg("Downloading %s - %s %s\n" % (file, size/1024, LINE_OVERWRITE_FULL) )
                        
                        if FetcherInstance.download_from_web(url, file, download_path) != True:
                            errlist.append(PackageName)
                        else:
                            if ArgumentOptions.deb_bugs:
                                bug_fetched = 0
                                if FetchBugReportsDebian.FetchBugsDebian(PackageName) in [1,2]:
                                    log.verbose("Fetched bug reports for package %s.\n" % (PackageName) )
                                    bug_fetched = 1
                                else:
                                    log.verbose("Couldn't fetch bug reports for package %s.\n" % (PackageName) )
                            
                            if ArgumentOptions.zip_it:
                                log.success("%s done.%s\n" % (PackageName, LINE_OVERWRITE_FULL) )
                                FetcherInstance.compress_the_file(zip_upgrade_file, file)
                                os.unlink(os.path.join(download_path, file))
                                
                                if bug_fetched:
                                    if FetchBugReportsDebian.AddToArchive(zip_upgrade_file):
                                        log.verbose("Archived bug reports for package %s to archive %s\n" % (PackageName, zip_upgrade_file) )
                                            
                    else:
                        if find_first_match(cache_dir, file, download_path, checksum) == False:
                            log.msg("Downloading %s - %d KB%s\n" % (PackageName, size/1024, LINE_OVERWRITE_MID) )
                            
                            if FetcherInstance.download_from_web(url, file, download_path) != True:
                                errlist.append(PackageName)
                            else:
                                log.success("%s done.%s\n" % (PackageName, LINE_OVERWRITE_FULL) )
                                if os.access(os.path.join(cache_dir, file), os.F_OK):
                                    log.verbose("%s file is already present in cache-dir %s. Skipping copy.\n" % (file, cache_dir) ) #INFO: The file is already there.
                                else:
                                    if os.access(cache_dir, os.W_OK):
                                        shutil.copy(file, cache_dir)
                                        log.verbose("%s copied to %s\n" % (file, cache_dir))
                                    else:
                                        log.verbose("Cannot copy %s to %s. Is %s writeable??\n" % (file, cache_dir))
                                        
                                if ArgumentOptions.deb_bugs:
                                    if FetchBugReportsDebian.FetchBugsDebian(PackageName) in [1,2]:
                                        log.verbose("Fetched bug reports for package %s.\n" % (PackageName) )
                                    else:
                                        log.verbose("Couldn't fetch bug reports for package %s.\n" % (PackageName) )
                                        
                                if ArgumentOptions.zip_it:
                                    if FetcherInstance.compress_the_file(zip_upgrade_file, file) != True:
                                        log.err("Couldn't add %s to archive %s.\n" % (file, zip_upgrade_file) )
                                        sys.exit(1)
                                    else:
                                        log.verbose("%s added to archive %s.\n" % (file, zip_upgrade_file) )
                                        os.unlink(os.path.join(download_path, file))
                                        
                        elif True:
                            if ArgumentOptions.deb_bugs:
                                bug_fetched = 0
                                if FetchBugReportsDebian.FetchBugsDebian(PackageName) in [1,2]:
                                    log.verbose("Fetched bug reports for package %s.\n" % (PackageName) )
                                    bug_fetched = 1
                                else:
                                    log.err("Couldn't fetch bug reports for package %s.\n" % (PackageName) )
                                    
                            if ArgumentOptions.zip_it:
                                if FetcherInstance.compress_the_file(zip_upgrade_file, file) != True:
                                    log.err("Couldn't add %s to archive %s.\n" % (file, zip_upgrade_file) )
                                    sys.exit(1)
                                else:
                                    log.verbose("%s added to archive %s.\n" % (file, zip_upgrade_file) )
                                    os.unlink(os.path.join(download_path, file))
                            else:
                                #Copy the bug report to the target download_path folder
                                if bug_fetched == 1:
                                    for x in os.listdir(os.curdir):
                                        if (x.startswith(PackageName) and x.endswith(pypt_bug_file_format) ):
                                            shutil.move(x, download_path)
                                            log.verbose("Moved %s file to %s folder.\n" % (x, download_path) )
                                
                else:
                    raise FetchDataKeyError
                    
    else:
        #INFO: Thread Support
        if ArgumentOptions.num_of_threads > 2:
            log.msg("WARNING: If you are on a slow connection, it is good to limit the number of threads to a low number like 2.\n")
            log.msg("WARNING: Else higher number of threads executed could cause network congestion and timeouts.\n\n")
            
        def run(request, response, func=find_first_match):
            '''Get items from the request Queue, process them
            with func(), put the results along with the
            Thread's name into the response Queue.
            
            Stop running when item is None.'''
        
            while 1:
                tuple_item_key = request.get()
                if tuple_item_key is None:
                    break
                (key, item) = tuple_item_key
                (url, file, download_size, checksum) = stripper(item)
                thread_name = threading.currentThread().getName()
                
                if key == 'Update':
                    temp_file = file.split("_")
                    PackageName = temp_file[0]
                    PackageName += " - " + temp_file[len(temp_file) - 1]
                    del temp_file
                    
                    #INFO: We pass None as a filename here because we don't want to do a tree search of
                    # update files. Update files are changed daily and there is no point in doing a search of
                    # them in the cache_dir
                    response.put(func(cache_dir, None) )
                    
                    #INFO: exit_status here would be False because for updates there's no need to do a
                    # find_first_match
                    # This is more with the above statement where None is passed as the filename
                    exit_status = response.get()
                    
                    if exit_status == False:
                        log.msg("Downloading %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) ) 
                        
                        if FetcherInstance.download_from_web(url, file, download_path) == True:
                            log.success("\r%s done.%s\n" % (PackageName, LINE_OVERWRITE_FULL) )
                            if ArgumentOptions.zip_it:
                                if FetcherInstance.compress_the_file(zip_update_file, file) != True:
                                    log.err("Couldn't archive %s to file %s.%s\n" % (file, zip_update_file, LINE_OVERWRITE_MID) )
                                    sys.exit(1)
                                else:
                                    log.verbose("%s added to archive %s.%s\n" % (file, zip_update_file, LINE_OVERWRITE_FULL) )
                                    os.unlink(os.path.join(download_path, file) )
                        else:
                            errlist.append(file)
                                
                elif key == 'Upgrade':
                    
                    try:
                        PackageName = file.split("_")[0]
                    except IndexError:
                        log.err("Not getting a package name here is problematic. Better bail out.\n")
                        sys.exit(1)
                    
                    #INFO: For Package version, we don't want to fail
                    try:
                        PackageVersion = file.split("_")[1]
                    except IndexError:
                        PackageVersion = "NA"
                        log.verbose("Weird!! Package version not present. Is it really a deb file?\n")
                    
                    def __numStr__( size):
                        if size > 1024:
                            size = size // 1024
                            if size > 1024:
                                size = size // 1024
                                return ("%d gB" % (size) )
                            return ("%d mB" % (size) )
                        return ("%d kB" % (size) )
                    
                    response.put(func(cache_dir, file) ) 
                    #INFO: find_first_match() returns False or a file name with absolute path
                    full_file_path = response.get()
                    
                    #INFO: If we find the file in the local cache_dir, we'll execute this block.
                    if full_file_path != False:
                        
                        # We'll first check for its md5 checksum
                        if ArgumentOptions.disable_md5check is False:
                            
                            if FetcherInstance.CheckHashDigest(full_file_path, checksum) is True:
                                log.verbose("md5checksum correct for package %s.%s\n" % (PackageName, LINE_OVERWRITE_FULL) )
                                
                                if ArgumentOptions.deb_bugs:
                                    bug_fetched = 0
                                    log.verbose("Fetching bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_FULL) )
                                    if FetchBugReportsDebian.FetchBugsDebian(PackageName) in [1,2]:
                                        log.verbose("Fetched bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_FULL) )
                                        bug_fetched = 1
                                    else:
                                        log.verbose("Couldn't fetch bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) )
                                
                                if ArgumentOptions.zip_it:
                                    
                                    if FetcherInstance.compress_the_file(zip_upgrade_file, full_file_path) is True:
                                        log.success("%s copied from local cache directory %s.%s\n" % (PackageName, cache_dir, LINE_OVERWRITE_MID) )
                                    else:
                                        log.err("Couldn't add %s to archive %s.%s\n" % (file, zip_upgrade_file, LINE_OVERWRITE_MID) )
                                        sys.exit(1)
                                            
                                #INFO: If no zip option enabled, simply copy the downloaded package file
                                # along with the downloaded bug reports.
                                else:
                                    try:
                                        shutil.copy(full_file_path, download_path)
                                        log.success("%s copied from local cache directory %s.%s\n" % (PackageName, cache_dir, LINE_OVERWRITE_MID) )
                                    except shutil.Error:
                                        log.verbose("%s already available in %s. Skipping copy!!!%s\n" % (file, download_path, LINE_OVERWRITE_MID) )
                                    
                                    if bug_fetched == 1:
                                        for x in os.listdir(os.curdir):
                                            if (x.startswith(PackageName) and x.endswith(pypt_bug_file_format) ):
                                                shutil.move(x, download_path)
                                                log.verbose("Moved %s file to %s folder.%s\n" % (x, download_path, LINE_OVERWRITE_FULL) )
                                        
                            #INFO: Damn!! The md5chesum didn't match :-(
                            # The file is corrupted and we need to download a new copy from the internet
                            else:
                                log.verbose("%s checksum mismatch. Skipping file.%s\n" % (file, LINE_OVERWRITE_FULL) )
                                log.msg("Downloading %s - %s %s\n" % (PackageName, __numStr__(download_size/1024), LINE_OVERWRITE_MID) )
                                if FetcherInstance.download_from_web(url, file, download_path) == True:
                                    log.success("\r%s done.%s\n" % (PackageName, LINE_OVERWRITE_FULL) )
                                    
                                    #Add to cache_dir if possible
                                    if ArgumentOptions.cache_dir and os.access(ArgumentOptions.cache_dir, os.W_OK) == True:
                                        try:
                                            shutil.copy(file, cache_dir)
                                            log.verbose("%s copied to local cache directory %s.%s\n" % (file, ArgumentOptions.cache_dir, LINE_OVERWRITE_MID) )
                                        except shutil.Error:
                                            log.verbose("Couldn't copy %s to %s.%s\n" % (file, ArgumentOptions.cache_dir, LINE_OVERWRITE_FULL) )
                                    else:
                                        log.verbose("cache_dir %s is not writeable. Skipping copy to it.\n" % (ArgumentOptions.cache_dir) )
                                        
                                            
                                    #Fetch bug reports
                                    if ArgumentOptions.deb_bugs:
                                        if FetchBugReportsDebian.FetchBugsDebian(PackageName) in [1,2]:
                                            log.verbose("Fetched bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) )
                                        else:
                                            log.verbose("Couldn't fetch bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) )
                                            
                                    if ArgumentOptions.zip_it:
                                        if FetcherInstance.compress_the_file(zip_upgrade_file, file) != True:
                                            log.err("Couldn't archive %s to file %s.%s\n" % (file, zip_upgrade_file, LINE_OVERWRITE_SMALL) )
                                            sys.exit(1)
                                        else:
                                            log.verbose("%s added to archive %s.%s\n" % (file, zip_upgrade_file, LINE_OVERWRITE_SMALL) )
                                            os.unlink(os.path.join(download_path, file) )
                                        
                        #INFO: You're and idiot.
                        # You should NOT disable md5checksum for any files
                        else:
                            if ArgumentOptions.deb_bugs:
                                bug_fetched = 0
                                if FetchBugReportsDebian.FetchBugsDebian(PackageName) in [1,2]:
                                    log.verbose("Fetched bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) )
                                    bug_fetched = 1
                                else:
                                    log.verbose("Couldn't fetch bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) )
                                    
                            #FIXME: Don't know why this was really required. If this has no changes, delete it.
                            #file = full_file_path.split("/")
                            #file = file[len(file) - 1]
                            #file = download_path + "/" + file
                            if ArgumentOptions.zip_it:
                                if FetcherInstance.compress_the_file(zip_upgrade_file, file) != True:
                                    log.err("Couldn't archive %s to file %s.%s\n" % (file, zip_upgrade_file, LINE_OVERWRITE_SMALL) )
                                    sys.exit(1)
                                else:
                                    log.verbose("%s added to archive %s.%s\n" % (file, zip_upgrade_file, LINE_OVERWRITE_SMALL) )
                                    os.unlink(os.path.join(download_path, file) )
                            else:
                                # Since zip file option is not enabled let's copy the file to the target folder
                                try:
                                    shutil.copy(full_file_path, download_path)
                                    log.success("%s copied from local cache directory %s.%s\n" % (file, cache_dir, LINE_OVERWRITE_SMALL) )
                                except shutil.Error:
                                    log.verbose("%s already available in dest_dir. Skipping copy!!!%s\n" % (file, LINE_OVERWRITE_SMALL) )
                                    
                                # And also the bug reports
                                if bug_fetched == 1:
                                    for x in os.listdir(os.curdir):
                                        if (x.startswith(PackageName) and x.endswith(pypt_bug_file_format) ):
                                            shutil.move(x, download_path)
                                            log.verbose("Moved %s file to %s folder.%s\n" % (x, download_path, LINE_OVERWRITE_MID) )
                                        
                    else:
                        #INFO: This block gets executed if the file is not found in local cache_dir or cache_dir is None
                        # We go ahead and try to download it from the internet
                        log.verbose("%s not available in local cache %s.%s\n" % (file, ArgumentOptions.cache_dir, LINE_OVERWRITE_MID) )
                        log.msg("Downloading %s %s - %s %s\n" % (PackageName, PackageVersion, __numStr__(download_size/1024), LINE_OVERWRITE_MID) )
                        if FetcherInstance.download_from_web(url, file, download_path) == True:
                            
                            #INFO: This block gets executed if md5checksum is allowed
                            if ArgumentOptions.disable_md5check is False:
                                #INFO: Debian moved to SHA256. So we use that now. Older systems could have md5
                                srcHash = checksum.split(":")[1]
                                hashType = checksum.split(":")[0]
                                log.verbose("srcHash is %s, hashType is %s\n" % (srcHash, hashType) )
                                if FetcherInstance.CompareHashDigest(file, srcHash, hashType) is True:
                                            
                                    if ArgumentOptions.cache_dir and os.access(ArgumentOptions.cache_dir, os.W_OK) == True:
                                        try:
                                            shutil.copy(file, ArgumentOptions.cache_dir)
                                            log.verbose("%s copied to local cache directory %s.%s\n" % (file, ArgumentOptions.cache_dir, LINE_OVERWRITE_MID) )
                                        except shutil.Error:
                                            log.verbose("%s already available in %s. Skipping copy!!!%s\n" % (file, ArgumentOptions.cache_dir, LINE_OVERWRITE_MID) )
                                    else:
                                        log.verbose("cache_dir %s is not writeable. Skipping copy to it.\n" % (ArgumentOptions.cache_dir) )
                                            
                                    if ArgumentOptions.deb_bugs:
                                        if FetchBugReportsDebian.FetchBugsDebian(PackageName) in [1,2]:
                                            log.verbose("Fetched bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) )
                                        else:
                                            log.verbose("Couldn't fetch bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) )
                                            
                                    if ArgumentOptions.zip_it:
                                        if FetcherInstance.compress_the_file(zip_upgrade_file, file) != True:
                                            log.err("Couldn't archive %s to file %s.%s\n" % (file, zip_upgrade_file, LINE_OVERWRITE_SMALL) )
                                            sys.exit(1)
                                        else:
                                            log.verbose("%s added to archive %s.%s\n" % (file, zip_upgrade_file, LINE_OVERWRITE_SMALL) )
                                            os.unlink(os.path.join(download_path, file) )
                                else:
                                    #INFO MD5 Checksum is incorrect.
                                    log.err("%s MD5 Checksum mismatch.\n" % (PackageName) )
                                    errlist.append(PackageName)
                                            
                            else:
                                if ArgumentOptions.deb_bugs:
                                    if FetchBugReportsDebian.FetchBugsDebian(PackageName) in [1,2]:
                                        log.verbose("Fetched bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) )
                                    else:
                                        log.verbose("Couldn't fetch bug reports for package %s.%s\n" % (PackageName, LINE_OVERWRITE_MID) )
                                        
                                if ArgumentOptions.zip_it:
                                    if FetcherInstance.compress_the_file(zip_upgrade_file, file) != True:
                                        log.err("Couldn't archive %s to file %s.%s\n" % (file, zip_upgrade_file, LINE_OVERWRITE_SMALL) )
                                        sys.exit(1)
                                    else:
                                        log.verbose("%s added to archive %s.%s\n" % (file, zip_upgrade_file, LINE_OVERWRITE_SMALL) )
                                        os.unlink(os.path.join(download_path, file) )
                                            
                            log.success("\r%s %s done.%s\n" % (PackageName, PackageVersion, LINE_OVERWRITE_FULL) )
                        else:
                            #log.err("Couldn't find %s\n" % (PackageName) )
                            errlist.append(PackageName)
                else:
                    raise FetchDataKeyError
        # Create two Queues for the requests and responses
        requestQueue = Queue.Queue()
        responseQueue = Queue.Queue()
        
        # Pool of NUMTHREADS Threads that run run().
        thread_pool = [
                       threading.Thread(
                              target=run,
                              args=(requestQueue, responseQueue)
                              )
                       for i in range(ArgumentOptions.num_of_threads)
                       ]
        
        # Start the threads.
        for t in thread_pool: t.start()
        
        # Queue up the requests.
        #for item in raw_data_list: requestQueue.put(item)
        for key in FetchData.keys():
            for item in FetchData.get(key):
                requestQueue.put( (key, item) )
        
        # Shut down the threads after all requests end.
        # (Put one None "sentinel" for each thread.)
        for t in thread_pool: requestQueue.put(None)
        
        # Don't end the program prematurely.
        #
        # (Note that because Queue.get() is blocking by
        # defualt this isn't strictly necessary. But if
        # you were, say, handling responses in another
        # thread, you'd want something like this in your
        # main thread.)
        for t in thread_pool: t.join()
                        
    # Print the failed files
    if len(errlist) == 0:
        log.msg("\nAll files have been downloaded.\n")
    else:
        log.err("\n\nThe following files failed to be downloaded.\n")
        for error in errlist:
            log.err("%s failed.\n" % (error))
        
        
def syncer(install_file_path, target_path, path_type=None, bug_parse_required=None):
    '''
    Syncer does the work of syncing the downloaded files.
    It syncs "install_file_path" which could be a valid file path
    or a zip archive to "target_path"
    path_type defines whether install_file_path is a zip file
    or a folder path
    
    # path_type
    1 => install_file_path is a File
    2 => install_file_path is a Folder
    '''
    
    archive = MyPythonLib.Archiver()
                
    def display_options():
        
        log.msg("(Y) Yes. Proceed with installation\n")
        log.msg("(N) No, Abort.\n")
        log.msg("(R) Redisplay the list of bugs.\n")
        log.msg("(Bug Number) Display the bug report from the Offline Bug Reports.\n")
        log.msg("(?) Display this help message.\n")
        
    def get_response():
        response = raw_input("What would you like to do next:\t (y, N, Bug Number, R, ?)" )
        response = response.rstrip("\r")
        return response
    
    def list_bugs():
        log.msg("\n\nFollowing are the list of bugs present.\n")
        for each_bug in bugs_number.keys():
            bug_num = each_bug.split('.')[1]
            bug_subject = bugs_number[each_bug]
            log.msg("%s\t%s\n" % (bug_num, bug_subject) )
            
    def magic_check_and_uncompress(archive_file=None, target_path=None, filename=None, Mode=None):
        
        if pypt_magic.file(archive_file) == "application/x-bzip2":
            retval = archive.decompress_the_file(archive_file, target_path, filename, 1)
        elif pypt_magic.file(archive_file) == "application/x-gzip":
            retval = archive.decompress_the_file(archive_file, target_path, filename, 2)
        elif pypt_magic.file(archive_file) == "application/zip":
            retval = archive.decompress_the_file(os.path.join(install_file_path, eachfile), target_path, eachfile, 3)
        elif pypt_magic.file(archive_file) == "PGP armored data" or pypt_magic.file(archive_file) == "application/x-dpkg":
            if os.access(target_path, os.W_OK):
                shutil.copy(archive_file, target_path + filename)
                retval = True
            else:
                log.err("Cannot write to target path %s\n" % (target_path) )
                sys.exit(1)
        elif filename.endswith(pypt_bug_file_format):
            retval = False # We intentionally put the bug report files as not printed.
        else:
            log.err("I couldn't understand file type %s.\n" % (filename) )
        if retval is True:
            log.msg("%s file synced.\n" % (filename))
        
    if path_type == 1:
        # We are doing a deb sync. Input mostly will be a zip file or a directory path
            
        file = zipfile.ZipFile(install_file_path, "r")
        if bug_parse_required is True:
                
            bugs_number = {}
            for filename in file.namelist():
                if filename.endswith(pypt_bug_file_format):
                    temp = tempfile.NamedTemporaryFile()
                    temp.file.write(file.read(filename))
                    temp.file.flush()
                    temp.file.seek(0) #Let's go back to the start of the file
                    for bug_subject_identifier in temp.file.readlines():
                        if bug_subject_identifier.startswith('#'):
                            subject = bug_subject_identifier.lstrip(bug_subject_identifier.split(":")[0])
                            subject = subject.rstrip("\n")
                            break
                    bugs_number[filename] = subject
                    temp.file.close()
                    
            if bugs_number:
                # Display the list of bugs
                list_bugs()
                display_options()
                response = get_response()
                
                while True:
                    if response == "?":
                        display_options()
                        response = get_response()
                        
                    elif response.startswith('y') or response.startswith('Y'):
                        for filename in file.namelist():
                            
                            data = tempfile.NamedTemporaryFile()
                            data.file.write(file.read(filename))
                            data.file.flush()
                            archive_file = data.name
                            
                            magic_check_and_uncompress(archive_file, target_path, filename)
                            data.file.close()
                        sys.exit(0)
                            
                    elif response.startswith('n') or response.startswith('N'):
                        log.err("Exiting gracefully on user request.\n\n")
                        sys.exit(0)
                        
                    elif response.isdigit() is True:
                        found = False
                        for full_bug_file_name in bugs_number:
                            if response in full_bug_file_name:
                                bug_file_to_display = full_bug_file_name
                                found = True
                                break
                        if found == False:
                            log.err("Incorrect bug number %s provided.\n" % (response) )
                            response = get_response()
                        
                        if found:
                            display_pager = PagerCmd()
                            retval = display_pager.send_to_pager(file.read(bug_file_to_display) )
                            if retval == 1:
                                log.err("Broken pager. Can't display the bug details.\n")
                            # Redisplay the menu
                            # FIXME: See a pythonic possibility of cleaning the screen at this stage
                            response = get_response()
                        
                    elif response.startswith('r') or response.startswith('R'):
                        list_bugs()
                        response = get_response()
                        
                    else:
                        log.err('Incorrect choice. Exiting\n')
                        sys.exit(1)
            else:
                log.msg("Great!!! No bugs found for all the packages that were downloaded.\n")
                response = raw_input("Continue with Installation. Y/N ?")
                response = response.rstrip("\r")
                if response.endswith('y') or response.endswith('Y'):
                    log.verbose("Continuing with syncing the files.\n")
                    for filename in file.namelist():
                        
                        data = tempfile.NamedTemporaryFile()
                        data.file.write(file.read(filename))
                        data.file.flush()
                        archive_file = data.name
                            
                        magic_check_and_uncompress(archive_file, target_path, filename)
                        data.file.close()
                else:
                    log.msg("Exiting gracefully on user request.\n")
                    sys.exit(0)
        elif bug_parse_required is False:
                
            for filename in file.namelist():
                
                data = tempfile.NamedTemporaryFile()
                data.file.write(file.read(filename))
                data.file.flush()
                archive_file = data.name
                            
                magic_check_and_uncompress(archive_file, target_path, filename)
                data.file.close()
        else:
            log.err("Inappropriate argument sent to syncer during data fetch. Do you need to fetch bugs or not?\n")    
            sys.exit(1)
            
    elif path_type == 2:
        archive_file_types = ['application/x-bzip2', 'application/gzip', 'application/zip']
        
        if bug_parse_required is True:
            bugs_number = []
            for filename in os.listdir(install_file_path):
                if filename.endswith(pypt_bug_file_format):
                    bugs_number.append(filename)
                    
            if bugs_number:
                #Give the choice to the user
                list_bugs()
                display_options()
                response = get_response()
                
                while True:
                    if response == "?":
                        display_options()
                        response = get_response()
                        
                    elif response.startswith('y') or response.startswith('Y'):
                        
                        for eachfile in os.listdir(install_file_path):
                            archive_type = None
                                
                            magic_check_and_uncompress(archive_file, target_path, filename)
                            
                    elif response.startswith('n') or response.startswith('N'):
                        log.err("Exiting gracefully on user request.\n\n")
                        sys.exit(0)
                        
                    elif response.isdigit() is True:
                        found = False
                        for full_bug_file_name in bugs_number:
                            if response in full_bug_file_name:
                                bug_file_to_display = full_bug_file_name
                                found = True
                                break
                        if found == False:
                            log.err("Incorrect bug number %s provided.\n" % (response) )
                            response = get_response()
                        
                        if found:
                            display_pager = PagerCmd()
                            retval = display_pager.send_to_pager(file.read(bug_file_to_display) )
                            if retval == 1:
                                log.err("Broken pager. Can't display the bug details.\n")
                            # Redisplay the menu
                            # FIXME: See a pythonic possibility of cleaning the screen at this stage
                            response = get_response()
                        
                    elif response.startswith('r') or response.startswith('R'):
                        list_bugs()
                        response = get_response()
                        
                    else:
                        log.err('Incorrect choice. Exiting\n')
                        sys.exit(1)
            else:
                log.msg("Great!!! No bugs found for all the packages that were downloaded.\n")
                response = raw_input("Continue with Installation. Y/N?")
                response = response.rstrip("\r")
                
                if response.startswith('y') or response.startswith('Y'):
                        
                    for eachfile in os.listdir(install_file_path):
                        archive_type = None
                            
                        magic_check_and_uncompress(archive_file, target_path, filename)
                else:
                    log.msg("Exiting gracefully on user request.\n")
                    sys.exit(0)
        elif bug_parse_required is False:
            for eachfile in os.listdir(install_file_path):
                archive_type = None
                    
                magic_check_and_uncompress(archive_file, target_path, filename)
        else:
            log.err("Inappropriate argument sent to syncer during data fetch. Do you need to fetch bugs or not?\n")    
            sys.exit(1)
                
                
def main():
    '''Here we basically do the sanity checks, some validations
    and then accordingly call the corresponding functions.'''
    
    """Contains most of the variables that are required by the application to run.
    Also does command-line option parsing and variable validation."""
    
    parser = optparse.OptionParser(usage="%prog [OPTION1, OPTION2, ...]",
                                   version="%prog " + version + "\n" + copyright)
       
    parser.add_option("-d","--download-dir", dest="download_dir",
                      help="Root directory path to save the downloaded files", action="store", type="string", metavar="pypt-downloads")
    parser.add_option("-s","--cache-dir", dest="cache_dir",
                      help="Root directory path where the pre-downloaded files will be searched.Make sure you give the full path of the cache directory. If not, give a period '.'",
                      action="store", type="string", metavar=".")
    parser.add_option("--verbose", dest="verbose", help="Enable verbose messages", action="store_true")
    parser.add_option("","--disable-md5check", dest="disable_md5check",
                      help="Disable md5checksum validation on downloaded files",action="store_false", default=False)
    parser.add_option("", "--threads", dest="num_of_threads", help="Number of threads to spawn",
                      action="store", type="int", metavar="1", default=1)
    parser.add_option("", "--test-windows", dest="test_windows", help="This switch is used while doing testing on windows.", action="store_true")
    parser.add_option("", "--socket-timeout", dest="socket_timeout", help="Set the socket timeout value. Default is 30s.",
                      action="store", type="int", metavar="30", default=30)
    parser.add_option("", "--gui", dest="gui", help="Run in Graphical Mode",
                      action="store_true")
       
    #INFO: Option zip is not enabled by default but is highly encouraged.
    parser.add_option("-z","--zip", dest="zip_it", help="Zip the downloaded files to a single zip file", action="store_true")
    parser.add_option("--zip-update-file", dest="zip_update_file", help="Default zip file for downloaded (update) data",
                      action="store", type="string", metavar="pypt-offline-update.zip", default="pypt-offline-update.zip")
    parser.add_option("--zip-upgrade-file", dest="zip_upgrade_file", help="Default zip file for downloaded (upgrade) data",
                      action="store", type="string", metavar="pypt-offline-upgrade.zip", default="pypt-offline-upgrade.zip")
       
    #INFO: At the moment nargs cannot be set to something like * so that optparse could manipulate n number of args. This is a limitation in optparse at the moment. The author might add this feature in the future.
    # When fixed by the author, we'd be in a better shape to use the above mentioned line instead of relying on this improper way.
    # With action="store_true", we are able to store all the arguments into the args variable from where it can be fetched later.
    #parser.add_option("", "--set-install-packages", dest="set_install_packages", help="Extract the list of uris which need to be fetched for installation of the given package and its dependencies", action="store", type="string", nargs=10, metavar="package_name")
    parser.add_option("", "--set-install", dest="set_install",
                      help="Extract the list of uris which need to be fetched for installation of the given package and its dependencies",
                      action="store", metavar="pypt-offline-install.dat")
    parser.add_option("", "--set-install-packages", dest="set_install_packages", help="Name of the packages which need to be fetched",
                      action="store_true", metavar="package_names")
    parser.add_option("", "--set-install-release", dest="set_install_release", help="Name of the release from which packages need to be fetched",
                      action="store", metavar="release_name")
       
    parser.add_option("", "--set-update", dest="set_update", help="Extract the list of uris which need to be fetched for updation",
                      action="store", type="string", metavar="pypt-offline-update.dat")
    parser.add_option("", "--set-upgrade", dest="set_upgrade", help="Extract the list of uris which need to be fetched for _upgradation_",
                      action="store", type="string", metavar="pypt-offline-upgrade.dat")
    parser.add_option("", "--upgrade-type", dest="upgrade_type",
                      help="Type of upgrade to do. Use one of upgrade, dist-upgrade, dselect-ugprade",
                      action="store", type="string", metavar="upgrade")
    
    parser.add_option("", "--fetch-update", dest="fetch_update",
                      help="Fetch the list of uris which are needed for apt's databases _updation_. This command must be executed on the WITHNET machine",
                      action="store", type="string", metavar="pypt-offline-update.dat")
    parser.add_option("", "--fetch-upgrade", dest="fetch_upgrade",
                      help="Fetch the list of uris which are needed for apt's databases _upgradation_. This command must be executed on the WITHNET machine",
                      action="store", type="string", metavar="pypt-offline-upgrade.dat")
    parser.add_option("", "--fetch-bug-reports", dest="deb_bugs",
                      help="Fetch bug reports from the BTS", action="store_true")
    
    parser.add_option("", "--install-update", dest="install_update",
                      help="Install the fetched database files to the  NONET machine and _update_ the apt database on the NONET machine. This command must be executed on the NONET machine",
                      action="store", type="string", metavar="pypt-offline-update.zip")
    parser.add_option("", "--install-upgrade", dest="install_upgrade",
                      help="Install the fetched packages to the  NONET machine and _upgrade_ the packages on the NONET machine. This command must be executed on the NONET machine",
                      action="store", type="string", metavar="pypt-offline-upgrade.zip")
    #global options, args
    (options, args) = parser.parse_args()
    
    # The log implementation
    # Instantiate the class
    global log
    log = MyPythonLib.Log(options.verbose, lock = True)
    
    try:
        if options.gui:
            if guiBool is True:
                
                class GUI(pyptofflineguiForm):
                    pass

                app = QApplication(sys.argv)
                QObject.connect(app, SIGNAL("lastWindowClosed()"), app, SLOT("quit()") )
                w = GUI()
                app.setMainWidget(w)
                w.show()
                app.exec_loop()
            else:
                log.err("Incomplete installation. PyQT or pypt-offline GUI libraries not available.\n")
                sys.exit(1)
        
        log.msg("pypt-offline %s\n" % (version))
        log.msg("Copyright %s\n" % (copyright))
        log.msg(terminal_license)
        
        if options.socket_timeout:
            try:
                options.socket_timeout.__int__()
                socket.setdefaulttimeout(options.socket_timeout)
                log.verbose("Default timeout now is: %d.\n" % (socket.getdefaulttimeout() ) )
            except AttributeError:
                log.err("Incorrect value set for socket timeout.\n")
                sys.exit(1)
                
        #INFO: Python 2.5 has hashlib which supports sha256
        # If we don't have Python 2.5, disable MD5/SHA256 checksum
        if MyPythonLib.Python_2_5 is False:
            options.disable_md5check = True
            log.verbose("\nMD5/SHA256 Checksum is being disabled. You need atleast Python 2.5 to do checksum verification.\n")
                
        if options.test_windows:
            global apt_package_target_path
            global apt_update_target_path
            apt_package_target_path = 'C:\\temp'
            apt_update_target_path = 'C:\\temp'
            
        if PythonApt is True:
            class AptPython:
                def __init__(self):
                    self.cache = apt.Cache()
                    
        
        if options.set_update:
            if platform.system() in supported_platforms:
                if os.geteuid() != 0:
                    parser.error("This option requires super-user privileges. Execute as root or use sudo/su")
                else:
                    log.msg("\n\nGenerating database of files that are needed for an update.\n")
                    
                    #FIXME: Unicode Fix
                    # This is only a workaround.
                    # When using locales, we get translation files. But apt doesn't extract the URI properly.
                    # Once the extraction problem is root-caused, we can fix this easily.
                    os.environ['__pypt_set_update'] = options.set_update
                    try:
                        old_environ = os.environ['LANG']
                    except KeyError:
                        old_environ = "C"
                    os.environ['LANG'] = "C"
                    log.verbose("Set environment variable for LANG from %s to %s temporarily.\n" % (old_environ, os.environ['LANG']) )
                    if os.system('/usr/bin/apt-get -qq --print-uris update > $__pypt_set_update') != 0:
                        log.err("FATAL: Something is wrong with the apt system.\n")
                        log.verbose("Set environment variable for LANG back to its original from %s to %s.\n" % (os.environ['LANG'], old_environ) )
                        os.environ['LANG'] = old_environ
                    log.verbose("Set environment variable for LANG back to its original from %s to %s.\n" % (os.environ['LANG'], old_environ) )
                    os.environ['LANG'] = old_environ
            else:
                parser.error("This argument is supported only on Unix like systems with apt installed\n")
            sys.exit(1)
     
        if options.set_upgrade or options.upgrade_type:
            if not (options.set_upgrade and options.upgrade_type):
                parser.error("Options --set-upgrade and --upgrade-type are mutually inclusive\n")
                     
            if platform.system() in supported_platforms:
                if os.geteuid() != 0:
                    parser.error("This option requires super-user privileges. Execute as root or use sudo/su")
                    
                #TODO: Use a more Pythonic way for it
                if options.upgrade_type == "upgrade":
                    
                    if PythonApt is True:
                        PythonAptQuery = AptPython()
                        try:
                            install_file = open(options.set_upgrade, 'w')
                        except IOError:
                            log.err("Cannot create file %s.\n" % (options.set_upgrade) )
                            sys.exit(1)
                            
                        upgradable = filter(lambda p: p.isUpgradable, PythonAptQuery.cache)
                        log.msg("\n\nGenerating database of files that are needed for an upgrade.\n")

                        dup_records = []
                        for pkg in upgradable:
                                pkg._lookupRecord(True)
                                path = apt_pkg.ParseSection(pkg._records.Record)['Filename']
                                checksum = apt_pkg.ParseSection(pkg._records.Record)['SHA256']
                                size = apt_pkg.ParseSection(pkg._records.Record)['Size']
                                cand = pkg._depcache.GetCandidateVer(pkg._pkg)
                                for (packagefile,i) in cand.FileList:
                                        indexfile = PythonAptQuery.cache._list.FindIndex(packagefile)
                                        if indexfile:
                                                uri = indexfile.ArchiveURI(path)
                                                file = uri.split('/')[-1]
                                                if checksum.__str__() in dup_records:
                                                    continue
                                                install_file.write(uri + ' ' + file + ' ' + size + ' ' + checksum + "\n")
                                                dup_records.append(checksum.__str__())

                    else:
                        log.msg("\n\nGenerating database of files that are needed for an upgrade.\n")
                        os.environ['__pypt_set_upgrade'] = options.set_upgrade
                        if os.system('/usr/bin/apt-get -qq --print-uris upgrade > $__pypt_set_upgrade') != 0:
                            log.err("FATAL: Something is wrong with the apt system.\n")
                elif options.upgrade_type == "dist-upgrade":
                    log.msg("\n\nGenerating database of files that are needed for a dist-upgrade.\n")
                    os.environ['__pypt_set_upgrade'] = options.set_upgrade
                    if os.system('/usr/bin/apt-get -qq --print-uris dist-upgrade > $__pypt_set_upgrade') != 0:
                        log.err("FATAL: Something is wrong with the apt system.\n")
                elif options.upgrade_type == "dselect-upgrade":
                    log.msg("\n\nGenerating database of files that are needed for a dselect-upgrade.\n")
                    os.environ['__pypt_set_upgrade'] = options.set_upgrade
                    if os.system('/usr/bin/apt-get -qq --print-uris dselect-upgrade > $__pypt_set_upgrade') != 0:
                        log.err("FATAL: Something is wrong with the apt system.\n")
                else:
                    parser.error("Invalid upgrade argument type selected\nPlease use one of, upgrade/dist-upgrade/dselect-upgrade\n")
            else:
                parser.error("This argument is supported only on Unix like systems with apt installed\n")
                sys.exit(1)
                 
        if options.set_install_packages or options.set_install:
            if not (options.set_install_packages and options.set_install):
                parser.error("Options --set-install and --set-install-package are mutually inclusive\n")
                
            if platform.system() in supported_platforms:
                if os.geteuid() != 0:
                    parser.error("This option requires super-user privileges. Execute as root or use sudo/su")
                    
                log.msg("\n\nGenerating database of the package and its dependencies.\n")
                os.environ['__pypt_set_install'] = options.set_install
                os.environ['__pypt_set_install_packages'] = ''
                
                #INFO: This is improper way of getting the args, the name of the packages.
                # But since optparse doesn't have the implementation in place at the moment, we're using it.
                # Once fixed, this will be changed.
                # For details look at the parser.add_option line above.
                for x in args:
                    os.environ['__pypt_set_install_packages'] += x + ' '
                    
                if options.set_install_release:
                    os.environ['__pypt_set_install_release'] = options.set_install_release
                    if os.system('/usr/bin/apt-get -qq --print-uris -t $__pypt_set_install_release install $__pypt_set_install_packages > $__pypt_set_install') != 0:
                        log.err("FATAL: Something is wrong with the apt system.\n")
                else:
                    #FIXME: Find a more Pythonic implementation
                    if os.system('/usr/bin/apt-get -qq --print-uris install $__pypt_set_install_packages > $__pypt_set_install') != 0:
                        log.err("FATAL: Something is wrong with the apt system.\n")
            else:
                parser.error("This argument is supported only on Unix like systems with apt installed\n")
                sys.exit(1)
               
        if options.fetch_update and options.fetch_upgrade:
            if os.access(options.fetch_update, os.F_OK) and os.access(options.fetch_upgrade, os.F_OK):
                log.msg("\nFetching uris which update apt's package database\n\n")
            	# Since we're in fetch_update, the download_type will be non-deb/rpm data
            	# 1 is for update packages 
            	# 2 is for upgrade packages
                fetcher(options, 1)
                sys.exit(0)
            else:
                log.err("\nFile not present. Check path.\n")
                sys.exit(1)
                
        if options.fetch_update:
            if os.access(options.fetch_update, os.F_OK):
                log.msg("\nFetching packages which need upgradation\n\n")
            	# Since we're in fetch_update, the download_type will be non-deb/rpm data
            	# 1 is for update packages 
            	# 2 is for upgrade packages
                fetcher(options, 2)
                sys.exit(0)
            else:
                log.err("\n%s file not present. Check path.\n" % (options.fetch_upgrade) )
                sys.exit(1)
                 
        if options.fetch_upgrade:
            if os.access(options.fetch_upgrade, os.F_OK):
                log.msg("\nFetching packages which need upgradation\n\n")
            	# Since we're in fetch_update, the download_type will be non-deb/rpm data
            	# 1 is for update packages 
            	# 2 is for upgrade packages
            	fetcher(options, 2)
            	sys.exit(0)
            else:
                log.err("\n%s file not present. Check path.\n" % (options.fetch_upgrade) )
                sys.exit(1)
                 
        if options.install_update:
            if options.test_windows:
                pass
            else:
                try:
                    if os.geteuid() != 0:
                        log.err("\nYou need superuser privileges to execute this option\n")
                        sys.exit(1)
                except AttributeError:
                    log.err("Are you really running the install command on a Debian box?\n")
                    sys.exit(1)
                
            if os.path.isfile(options.install_update) is True:
                # Okay! We're a file. It should be a zip file
                syncer(options.install_update, apt_update_target_path, 1, bug_parse_required = False)
            elif os.path.isdir(options.install_update) is True:
                # We're a directory
                syncer(options.install_update, apt_update_target_path, 2, bug_parse_required = False)
            else:
                log.err("%s file not found\n" % (options.install_update))
                sys.exit(1)
            
        if options.install_upgrade:
            if options.test_windows:
                pass
            else:
                try:
                    if os.geteuid() != 0:
                        log.err("\nYou need superuser privileges to execute this option\n")
                        sys.exit(1)
                except AttributeError:
                    log.err("Are you really running the install command on a Debian box?\n")
                    sys.exit(1)
                    
            if os.path.isfile(options.install_upgrade) is True:
                syncer(options.install_upgrade, apt_package_target_path, 1, bug_parse_required = True)
            elif os.path.isdir(options.install_upgrade) is True:
                syncer(options.install_upgrade, apt_package_target_path, 2, bug_parse_required = True)
            else:
                log.err("%s file not found\n" % (options.install_upgrade))
                sys.exit(1)
            
    except KeyboardInterrupt:
        log.err("\nInterrupted by user. Exiting!\n")
        sys.exit(0)        
