# Use miniconda runtime as parent image
FROM continuumio/miniconda3

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

#COPY environment.yml /app/environment.yml
# create conda environment specified in environment.yml
RUN conda env create -f ./app/environment.yml

# Activate conda environment
RUN echo "source activate waveapp" > ~/.bashrc

# Make port 4000 available to the world outside this container
EXPOSE 4000

# Add conda environment to path
ENV PATH /opt/conda/envs/waveapp/bin:$PATH

ENTRYPOINT ["python", "./app/index.py"]
