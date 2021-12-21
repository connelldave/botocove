# Profiling Botocove

Logging the memory of a running process is surprisingly complicated.

Some options I considered for the task:

* https://github.com/sysstat/sysstat/blob/master/pidstat.c
* https://github.com/ColinIanKing/smemstat
* https://heptapod.host/saajns/procpath
* https://docs.python.org/3/library/tracemalloc.html

In the end, as the least bad option, I used a bash script to run top in a loop.

