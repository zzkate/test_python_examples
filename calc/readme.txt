Confines:
Application works only with inetgers( float delimiter isn't supported),
supported operations: () /* +-
functions are not supported

calculated results are stored during server runtime,
they are not available after server restart (no saving and restoring data via db or file on drive)
after server restart - pids from previous session are not actual

1) start http server
 python PATH_TO_UVICORN/uvicorn main:app

2) send post request via curl
curl -X POST -H "Content-Type: application/json" -d @/home/kate/Documents/dev/calc/data/data1.json http://localhost:8000/calculate

or run run_8_posts.sh (it runs 30 * 7 post requests in parallel)

3) open in web browser to monitor calculating process and get result for process with [pid]
http://127.0.0.1:8000/result?id=[pid]

4) stress testing
start server manually
start stress_test.py --url "http://127.0.0.1:8000" --process_num 200 ( or start with default parameters )


