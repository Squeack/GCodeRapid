# GCodeRapid
Look for high tool moves at cutting speed, and make them rapids

Usage: \path\to\python\python3.exe GCodeRapid.py -I \path\to\gcode\input.nc -O \path\to\gcode\output.nc

The option -A filename will produce a file annotated with what is going on - used for debugging. 
If -O is not specified then it will default to adding _rapid to the input file name.

Should work in Linux or other python environments too.
