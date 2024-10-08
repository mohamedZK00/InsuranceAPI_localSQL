import os
from fastapi import FastAPI
from pydantic import BaseModel
from pycaret.regression import load_model, predict_model
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import joblib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# تحميل النموذج
model_dir = os.path.dirname(os.path.realpath(__file__))  # المسار إلى الدليل الحالي
model_path = os.path.join(model_dir, '1-Insurance_model')  # إضافة اسم النموذج

# طباعة المسار للتحقق
print(f"Loading model from: {model_path}")

try:
    # استخدام load_model من pycaret
    model = load_model(model_path)
except Exception as e:
    print(f"Failed to load model with pycaret: {e}")
    try:
        # محاولة استخدام joblib مباشرة لتحميل النموذج
        model = joblib.load(model_path)
        print("Model loaded successfully with joblib.")
    except Exception as e:
        print(f"Failed to load model with joblib: {e}")
        raise e  # رفع الاستثناء إذا لم يتم التحميل

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InsurancePRED(BaseModel):
    age: int
    sex: str
    bmi: float
    children: int
    smoker: str
    region: str

# Function to get database connection using environment variables
def get_connection():
    try: 
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is not set in the environment.")
        conn = psycopg2.connect(database_url)
        return conn
        
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
   
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



