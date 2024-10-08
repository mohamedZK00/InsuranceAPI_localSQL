import os
from fastapi import FastAPI
from pydantic import BaseModel
from pycaret.regression import load_model, predict_model
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
import psycopg2

app = FastAPI()

# load model
#model = load_model('insurance_Model')
working_dir = os.path.dirname(os.path.realpath(__file__))
model_path = os.path.join(working_dir, '')

with open(model_path, 'rb') as f:
    model = pickle.load(f)

class InsurancePRED(BaseModel):
    age: int
    sex: str
    bmi: float
    children: int
    smoker: str
    region: str


# Function to get database connection using environment variables
def get_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'insurance_prediction'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'admin'),
        port=os.getenv('DB_PORT', '5432')
    )
    return conn


def db_created():
    try:
        conn = get_connection()
        if conn is None:
            return {"error": "Connection to PostgreSQL failed during table creation-1"}

        cursor = conn.cursor()

        cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS insu_predict(
                id SERIAL PRIMARY KEY,
                age INT,
                sex TEXT,
                bmi FLOAT,
                children INT,
                smoker TEXT,
                region TEXT,
                predictions FLOAT );  
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Table creation error ==> : {e}")

# Create table when the app starts
db_created()


@app.post('/predict')
def FUNprediction(input_data: InsurancePRED):
    try:
        conn = get_connection()
        if conn is None:
            return {"error": "Connection to PostgreSQL failed during prediction-2"}

        cursor = conn.cursor()
        data = pd.DataFrame([input_data.dict()])
        predictions = predict_model(model, data=data)

        # Insert input_data into DB
        cursor.execute(
            "INSERT INTO insu_predict (age, sex, bmi, children, smoker, region, predictions) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (input_data.age, input_data.sex, input_data.bmi, input_data.children, input_data.smoker, input_data.region,
             float(round(predictions["prediction_label"].iloc[0], 2))))
        conn.commit()
        cursor.close()
        conn.close()

        print('Predicted charges:', round(predictions["prediction_label"].iloc[0], 2))
        return {"message": "Data Added Successfully", 'Predicted charges': round(predictions["prediction_label"].iloc[0], 2)}

    except psycopg2.Error as e:
        print(f"Prediction error: {e}")
        return {"error": "Failed to add predictions to table"}




