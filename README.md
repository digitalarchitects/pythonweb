# pythonweb
an attempt to create a web app in python

You upload a normal CSV file with comma delimter.  
It returns a csv file with pipe delimiter.  
It transforms the fields to ensure they conform.

## Run locally (dev)
1. install python3 - `apt install python3`
2. create a virtual env - `python3 -m venv myenv`
3. install dependencies - `pip install -r requirements.txt`
4. run the program - `python3 app.py`
5. open http://127.0.0.1:5000

Make sure the `uploads/` directory exists in the project root:
```
mkdir -p uploads
```

## Run in Docker
Build and run a container (binds port 5000 and persists uploads locally):
```
docker build -t pythonweb:latest .
docker run -p 5000:5000 -v "$(pwd)/uploads":/app/uploads pythonweb:latest
```
Open http://127.0.0.1:5000

This image runs the app using gunicorn (production-ready server). The container exposes port 5000 by default.

## Run with docker-compose
docker-compose will mount `./uploads` and publish port 5000:
```
docker-compose up --build
```
Stop with `docker-compose down`.

Notes:
- Gunicorn is used in the Dockerfile for production-grade serving. For quick local testing you can keep using `python3 app.py`.
- If you need HTTPS, put the container behind a reverse proxy (nginx) or use a cloud load balancer.

