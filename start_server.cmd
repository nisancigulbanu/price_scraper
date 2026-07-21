@echo off
cd /d C:\Users\gulba\Desktop\price_cb_scraper
set "PATH=C:\msys64\ucrt64\bin;C:\msys64\usr\bin;%PATH%"
C:\msys64\ucrt64\bin\python.exe -m price_tracker.main --serve --host 127.0.0.1 --port 8000 > data\server.out.log 2> data\server.err.log
