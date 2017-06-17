FROM python:3.6.1
RUN pip install requests gitpython beautifulsoup4
RUN mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts
COPY . /checkouted/

ENV CONTINUOUS true
ENV INTERVAL 15

RUN chmod +x /checkouted/docker/run.sh

CMD ["/checkouted/docker/run.sh"]
