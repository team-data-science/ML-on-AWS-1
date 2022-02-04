FROM python:3.8.6-buster
RUN pip3 install --upgrade pip && pip3 install poetry

COPY poetry.lock pyproject.toml ./
RUN poetry install

COPY . .
EXPOSE 8501
CMD poetry run streamlit run src/app.py
