FROM python:3.9.15-slim
WORKDIR app/

COPY requirements.txt requirements.txt
COPY . .
RUN pip3 install -r requirements.txt

CMD [ "python3", "kindness.py"]
