# ML-on-AWS-1
Repo for the ML on AWS 1 course

## Postgres 
create the table with
```sql
CREATE TABLE guardian_posts_analytics(
	author varchar(50),
	timestamp timestamp with time zone,
	text varchar(300),
	sentiment_score double precision,
	PRIMARY KEY(author, timestamp)
	)
```

## K-Layers
Go to `Function Overview > Layers > Add a layer` 
![](assets/lambda-layers.png)
Under `Choose a layer > Specify an ARN` and add the following:

`arn:aws:lambda:eu-central-1:770693421928:layer:Klayers-python38-nltk:47` 
`arn:aws:lambda:eu-central-1:770693421928:layer:Klayers-python38-pytz:5` 
`arn:aws:lambda:eu-central-1:770693421928:layer:Klayers-python38-pandas:37` 

if you are in a different region (i.e. `us-east-1`), replace the region name. If that gives error,
 look up the layer exist, by replacing your region in the url below

`https://api.klayers.cloud/api/v1/layers/latest/{region}/{layer-name}` 

Example: 

https://api.klayers.cloud/api/v1/layers/latest/us-east-1/pytz 

https://api.klayers.cloud/api/v1/layers/latest/us-east-1/nltk 


## Local setup
Not necessary but if we students want to run code locally it would be better to create a virtual environment with `conda` and install the following

If you are on windows 
- install anaconda3 at https://www.anaconda.com/products/individual
- start the Anaconda3 power shell
- set the environment variables:
```
[Environment]::SetEnvironmentVariable("GUARDIAN_API_KEY", "Your-api-key", "User")
[Environment]::SetEnvironmentVariable("S3_BUCKET_NAME", "my-guardianpost-analytics-storage", "User")
[Environment]::SetEnvironmentVariable("DB_PASSWORD", "password", "User")
[Environment]::SetEnvironmentVariable("DB_HOST", "your-RDS-endpoint", "User")
```
 
```sh
conda create --name guardianpost_analytics_py38 python=3.8 spyder
conda activate guardianpost_analytics_py38
conda install -c conda-forge poetry # dependency management
conda install -c conda-forge notebook # for jupyter
```

to install the project dependencies run
```sh
poetry install
```

After the tutorial and setting `environmental variables`, you can run locally the dashboard with
```
poetry run streamlit run src/app.py
```
