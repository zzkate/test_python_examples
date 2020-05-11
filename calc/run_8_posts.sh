#bin/bash

for j in {0..30}
do
  for i in {1..8}
  do
    curl -X POST -H "Content-Type: application/json" -d @/home/kate/Documents/dev/calc/data/data$i.json http://localhost:8000/calculate &
  done
done