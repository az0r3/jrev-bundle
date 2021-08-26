### Android/Java reverse engineering bundle  

This is a convenience bundle mainly for Android apps reverse engineering.  
`$ git clone --recurse-submodules https://github.com/az0r3/jrev-bundle.git`

Runs on linux, needs unzip, python3, JDK, gradle, mvn.  

The repo contains:
* 3rd-party tools (and build wrappers) for unpacking/disassembling/decompiling java-based apps.
* `rev.py` -- a simple wrapper for running chain of tools on apk/dex/jar files.
* `update.sh` -- update and build all tools.

#### rev.py

This tool will try to generate source code of provided app.  
Some decompilers can benefit from information about external classes: you can provide library jar paths with `-l` option.  
Most successful decompiler varies from case to case. The optimal way is to start with fernflower and cfr.  

```
usage: rev.py [-h] [-d DECOMPILER] [-o OUTPUT_DIR] [-e EXT] [-m MAX_MEM_PCT]
              [-l LIBRARY_FILES]
              file

positional arguments:
  file              file to decompile. Supported extensions: apk, dex, jar

optional arguments:
  -h, --help        show this help message and exit
  -d DECOMPILER     decompiler name to use
                    one of: cfr, fernflower, jadx, jd, procyon, krakatau
  -o OUTPUT_DIR     dir to store results in, default=${file}.rev
  -e EXT            treat target file as specified extension
                    one of: apk, dex, jar
  -m MAX_MEM_PCT    upper RAM limit for java programs, in percent of current free RAM (default: 0.75)
  -l LIBRARY_FILES  library file(s) (may be useful for decompiler); example:
                    -l ~/Android/Sdk/platforms/android-28/android.jar
                    -l ~/Android/Sdk/platforms/android-28/optional/org.apache.http.legacy.jar
```
