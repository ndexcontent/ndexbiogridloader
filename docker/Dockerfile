# Use an official Python runtime as a parent image
FROM continuumio/miniconda3

RUN apt-get update
RUN apt-get install -y build-essential 

RUN mkdir /tmp/ndexbiogridloader
COPY ./ /tmp/ndexbiogridloader/
RUN pip install /tmp/ndexbiogridloader

RUN rm -rf /tmp/ndexbiogridloader

RUN mkdir /ndexbiogridloader
WORKDIR /ndexbiogridloader

CMD /bin/echo "To use run: ndexloadbiogrid.py"
