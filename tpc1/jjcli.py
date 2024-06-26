""" 
# Name

 jjcli - python module for command-line filter

Synopsis
========

as ascript:

    jjcli skel     ## a initial filter skeleton
    jjcli          ## manual

as a module: 

    from jjcli import *       ## re.* functions also imported
    cl=clfilter(opt="do:")     ## options in cl.opt  (...if "-d" in cl.opt:)
                              ##    autostrip         (def=True)
                              ##    inplace           (def=False) 
                              ##    fs (for csvrow()) (def=",")
                              ##    longopts=["opt1", ...] (def=[])
                              ##    doc=__doc__    (def="FIXME no doc pfovided")

    for line in cl.input():...    ## process one rstriped line at the time
    for txt in cl.text():...      ## process one striped text at the time (also
cl.slurp)
       ## process txt            ##   (end of line spaces and \r also removed)
    for par in cl.paragraph():... ## process one striped paragraph at the time
    for tup in cl.csvrow():...    ## process one csv row at the time
    for tup in cl.tsvrow():...    ## process one tsv row at the time

    cl.lineno()                ## line number
    cl.filelineno()
    cl.parno()                 ## paragraph number
    cl.fileparno()
    cl.filename()              ## filename or "<stdin>"
    cl.nextfile()
    cl.isfirstline()
    cl.args  cl.opt             ## command line arguments and options (after clfilter())

# Description

__jjcli__ is a opinioned Python module that tries to simplify the creation of
__unix__ filters. It is based on:

- getopt  (for command line options and args)
- fileinput (for [files/stdin] arguments)
- re (regular expressions should be native)
- glob (glob.glob should be native)
- csv  (for csv and tsv inputs)
- urllib.request (to deal with input argumens that are url)
- subprocess 

## Regular expressions

We want to have all re.* functions available (as if they were native
functions).

In order to enable __re__ flags, use: re.I re.X re.S  

## Subprocesses   (qx, qxlines, qxsystem)

    a=qx( "ls" )
    for x in qxlines("find | grep '\.jpg$'"): 
      ...
    qxsystem("vim myfile")

### Execute command return its stdout

    qx(*x)      →  returns    subprocess.getoutput(x)

### Execute command return its stdout lines

    qxlines(*x) →  returns    subprocess.getoutput(x).splitlines()

### Execute command -- system

    qxsystem(*x) →  calls     subprocess.call(x,shell=True)

## STDERR - warn, die

    warn(*args)  → print to stderr
    die(*args)   → warn and exit 1

## Other functions

    slurpurlutf8(self,f)

    filename    = lambda s : F.filename()      # inherited from fileinput
    lineno      = lambda s : F.lineno()
    filelineno  = lambda s : F.filelineno()
    parno       = lambda s : s.parno_          # paragraph number
    fileparno   = lambda s : s.fileparno_
    nextfile    = lambda s : F.nextfile()
    isfirstline = lambda s : F.isfirstline()
    isfirstpar  = lambda s : s.fileparno == 1
    close       = lambda s : F.close()

"""

import subprocess 
import inspect
from subprocess import PIPE
import re
from glob import glob
from re import match, fullmatch, search, sub, subn, split, findall, finditer, compile 
                    ## all re functions are imported!
                    ## and re.I re.S re.X 
import fileinput as F, getopt, sys
import urllib.request as ur, csv

## execute external comands

# execute command return its stdout
def qx(*x)      : return subprocess.getoutput(str.join(" ",x))

# execute command return its stdout lines
def qxlines(*x) : return subprocess.getoutput(str.join(" ",x)).splitlines()

# execute command -- system
def qxsystem(*x): subprocess.call(str.join(" ",x),shell=True)

# execute command -- popen
# def qxopen(cmd, mode="r"): 
#     if mode == "w":
#        proc = subprocess.Popen(cmd, shell=True,text=True, encoding="utf-8", stdin=PIPE)
#        return proc.stdin
#     else:
#        proc = subprocess.Popen(cmd, shell=True,text=True, encoding="utf-8", stdout=PIPE)
#        return proc.stdout

def die(*s,**kwargs):
    warn(*s,**kwargs)
    sys.exit(1)

def warn(*a,**kwargs):
    print(*a,file=sys.stderr,**kwargs)

## Command line filters
class clfilter:
   '''csfilter - Class for command line filters'''
   
   def __init__(self,opt="",
                     longopts=[],
                     rs="\n",
                     fs=",",
                     autostrip=True,
                     files=[],
                     doc="FIXME: no doc provided",
                     inplace=False):
       opcs=[]
       
       if isinstance( files, str): files = [files]
       if isinstance(opt,dict):
           self.opt, self.args = (opt, files)
       else:
           try:
               opts, args = getopt.getopt(sys.argv[1:],opt,longopts+["help"])
           except Exception as err:
               die(err)  
               # usage()
               sys.exit(1)
           self.opt=dict(opts)
           self.args=args + files
       if "--help" in self.opt :
           # print(__import__(caller_name[1]).__doc__ )
           print(doc.strip())
           sys.exit(0)
       self.rs=rs
       self.fs=fs
       self.autostrip=autostrip
       self.inplace=inplace
       self.text=self.slurp
       self.enc=F.hook_encoded("utf-8")
 
   def input(self,files=None): 
       files = files or self.args
       if self.autostrip:
           return map(str.rstrip,F.input(files=files,inplace=self.inplace,openhook=self.enc))
       else:
           return F.input(files=files,inplace=self.inplace,openhook=self.enc)

   def csvrow(self,files=None):
       files = files or self.args
       return csv.reader(F.input(files=files,openhook=self.enc),
                         skipinitialspace=True, delimiter=self.fs)

   def tsvrow(self,files=None):
       files = files or self.args
       return csv.reader(F.input(files=files,openhook=self.enc),
                         skipinitialspace=True, delimiter="\t")

   def paragraph(self,files=None):
       files = files or self.args or [None]
       self.parno_=0
       for f in files:
           t=""
           state=None
           self.fileparno_=0
           fs = [] if f == None else [f]
           for l in F.input(files=fs,inplace=self.inplace,openhook=self.enc):
               if search(r'\S', l) and state == "inside delim":
                   self.parno_+= 1
                   self.fileparno_+= 1
                   if self.autostrip:
                       yield self.cleanpar(t)
                   else:
                       yield t
                   state ="inside par"
                   t=l
               elif search(r'\S', l) and state != "inside delim":
                   t += l
                   state ="inside par"
               else:
                   state ="inside delim"
                   t += l
           if search(r'\S',t):             ## last paragraph
               self.parno_+= 1
               self.fileparno_+= 1
               if self.autostrip:
                   yield self.cleanpar(t)
               else:
                   yield t

   def off_slurp(self,files=None):
       files = files or self.args or [None]
       for f in files:
           t=""
           fs = [] if f == None else [f]
           for l in F.input(files=fs,inplace=self.inplace):
               t += l
           if self.autostrip:
               yield self.clean(t)
           else:
               yield t

   def slurp(self,files=None):
       files = files or self.args or [None]
       for f in files:
           t=""
           if f == None: fs=[]
           elif match(r'(https?|ftp)://',f):
               yield ur.urlopen(f).read().decode('utf-8')
               continue
           else: fs = [f]

           for l in F.input(files=fs,inplace=self.inplace,openhook=self.enc):
               t += l
           if self.autostrip:
               yield self.clean(t)
           else:
               yield t

   def slurpurlutf8(self,f):
       t= ur.urlopen(f).read()
       try:  
           a = t.decode('utf-8')
           return a
       except Exception as e1:
           try:  
               a = t.decode('iso8859-1')
               return a
           except Exception as e:
               return t

   def clean(self,s):              # clean: normalise end-of-line spaces and termination
       return sub(r'[ \r\t]*\n','\n',s)

   def cleanpar(self,s):           # clean: normalise end-of-line spaces and termination
       return sub(r'\s+$','\n' ,sub(r'[ \r\t]*\n','\n',s))

   filename    = lambda s : F.filename()      # inherited from fileinput
   filelineno  = lambda s : F.filelineno()
   lineno      = lambda s : F.lineno()
   fileparno   = lambda s : s.fileparno_
   parno       = lambda s : s.parno_
   nextfile    = lambda s : F.nextfile()
   isfirstline = lambda s : F.isfirstline()
   isfirstpar  = lambda s : s.fileparno_ == 1
   close       = lambda s : F.close()

#   filename    = F.filename()      # não funciona assim...

__version__ = "0.1.23"
__docformat__ = 'markdown'

def main():
   if   len(sys.argv)==1: 
      print("Name\n jjcli - ",__doc__.lstrip())

   elif len(sys.argv)==3 and sys.argv[1] == "skel" and sys.argv[2] == "line":
      print( """#!/usr/bin/python3
from jjcli import * 
'''
NAME
 filter that

SYNOPSYS

Description
'''
cl=clfilter(opt="ho:")     ## option values in cl.opt dictionary

for line in cl.input():    ## process one line at the time
    pass ## process line

""")  

   elif len(sys.argv)==3 and sys.argv[1] == "skel" and sys.argv[2] == "text":
      print( """#!/usr/bin/python3
from jjcli import * 
'''
NAME
 filter that

SYNOPSIS

Description
'''
cl=clfilter(opt="ho:", doc=__doc__)     ## option values in cl.opt dictionary

for txt in cl.text():     ## process one file at the time
    pass ## process file

""")  

   elif sys.argv[1] == "skel":
      print(
"""#!/usr/bin/python3
'''
NAME
   myscript - ...

SYNOPSIS
   myscript ...

Description'''

from jjcli import * 
cl=clfilter(opt="do:", doc=__doc__)     ## option values in cl.opt dictionary

for line in cl.input():    ## process one line at the time
    pass ## process line

#for txt in cl.text(): ...     ## process one file at the time
#for par in cl.paragraph():... ## process one paragraph at the time
#for txt in cl.cvsrow(): ...   ## process one csv row at the time
#for txt in cl.tvsrow(): ...   ## process one tsv row at the time
""")

if __name__ == "__main__": main()
