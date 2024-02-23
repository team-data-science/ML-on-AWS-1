# 
import requests
import pandas as pd
from pathlib import Path 

# Register as a developer on the Guardian website to get the key: https://open-platform.theguardian.com/
# Root Endpoint replace [your key here] with our API key
BASE_URL = "https://content.guardianapis.com/search?from-date=2024-02-23&order-by=newest&page=1&page-size=20&q=news&api-key=[your key here]"
# query data with GET - get all beers as json
response = requests.get(f'{BASE_URL}')
#print(response.status_code)
# > 200

resonse_json = response.json()
df=pd.json_normalize(resonse_json['response']["results"])


print(df.dtypes)
print(df.head())

ex_df = df.loc[:, ['webTitle', 'webPublicationDate']]
ex_df.to_csv("guardian_output.csv")


