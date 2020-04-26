1) start http server
 python PATH_TO_UVICORN/uvicorn main:app
 start redis
 docker start funbox_redis

2) send post request to the server:
curl -X POST -H "Content-Type: application/json" -d @/home/kate/Documents/dev/funbox/data.json http://localhost:8000/visited_links

to fill redis with data


3) open in web browser
http://127.0.0.1:8000/visited_domains?from=1545221231&to=1545217638

to extract filltered data
