# molla_bricks/core/services/ai_service.py
import pandas as pd
import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
import joblib

class AIService:
    def __init__(self, db_controller):
        self.db_controller = db_controller
        # Model for anomaly detection
        self.anomaly_model_path = "data/expense_model.json"
        self.anomaly_model = self._load_json_model(self.anomaly_model_path)
        # Model for category classification
        self.category_model_path = "data/category_classifier.joblib"
        self.category_model = self._load_joblib_model(self.category_model_path)

    def _load_json_model(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f: return json.load(f)
        return {}

    def _load_joblib_model(self, path):
        if os.path.exists(path):
            return joblib.load(path)
        return None

    def train_all_models(self):
        """A single function to train all available AI models."""
        msg1 = self.train_anomaly_model()
        msg2 = self.train_category_model()
        return f"{msg1}\n{msg2}"

    def train_anomaly_model(self):
        query1 = "SELECT category, amount FROM daily_expenses"
        daily_expenses_df = pd.DataFrame(self.db_controller.execute_query(query1, fetch="all"), columns=['category', 'amount'])
        query2 = "SELECT paid_amount FROM salary_payments"
        salary_df = pd.DataFrame(self.db_controller.execute_query(query2, fetch="all"), columns=['amount'])
        salary_df['category'] = 'Salary'
        all_expenses = pd.concat([daily_expenses_df, salary_df], ignore_index=True)
        if all_expenses.empty: return "No expense data to train anomaly model."
        
        stats = all_expenses.groupby('category')['amount'].agg(['mean', 'std']).dropna()
        self.anomaly_model = stats.to_dict('index')
        with open(self.anomaly_model_path, 'w') as f: json.dump(self.anomaly_model, f, indent=4)
        return "Anomaly detection model trained."

    def train_category_model(self):
        """Trains a text classifier on expense descriptions."""
        query = "SELECT description, category FROM daily_expenses"
        df = pd.DataFrame(self.db_controller.execute_query(query, fetch="all"), columns=['description', 'category'])
        
        # Need at least 2 categories and a few samples to train
        if df.empty or df['category'].nunique() < 2 or len(df) < 5:
            return "Not enough data to train category prediction model."
            
        # Create a machine learning pipeline
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer()),
            ('clf', SGDClassifier(loss='hinge', penalty='l2', alpha=1e-3, random_state=42, max_iter=5, tol=None)),
        ])
        
        pipeline.fit(df['description'], df['category'])
        joblib.dump(pipeline, self.category_model_path)
        self.category_model = pipeline # Update in-memory model
        return "Category prediction model trained."

    def predict_expense_category(self, description):
        """Predicts the category for a given expense description."""
        if not self.category_model or not description:
            return None
        try:
            # The model expects a list of items to predict
            prediction = self.category_model.predict([description])
            return prediction[0]
        except Exception:
            return None

    def is_expense_anomaly(self, category, amount):
        if not self.anomaly_model or category not in self.anomaly_model: return False
        stats = self.anomaly_model[category]; mean = stats['mean']; std_dev = stats.get('std', 0)
        if std_dev == 0: return amount > mean * 1.5
        threshold = mean + (2 * std_dev) 
        return amount > threshold and amount > mean * 1.2