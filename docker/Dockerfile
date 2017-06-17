FROM python:3.6.1
RUN pip install requests gitpython beautifulsoup4
RUN mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts
COPY . /checkouted/

ENV TZ=Europe/Prague
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV CONTINUOUS true
ENV INTERVAL 15

RUN chmod +x /checkouted/docker/run.sh

CMD ["/checkouted/docker/run.sh"]
