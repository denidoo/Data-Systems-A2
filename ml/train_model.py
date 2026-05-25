import joblib
import pandas as pd
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier

from ml.feature_engineering import (
    build_training_dataset,
    prepare_features,
    get_feature_columns
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "flight_delay_model.pkl"


def build_preprocessor():
    numeric_features, categorical_features = get_feature_columns()

    numeric_transformer = Pipeline(
        steps=[
            ("scaler", StandardScaler())
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    return preprocessor


def get_models():
    return {
        "Decision Tree": DecisionTreeClassifier(
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42
        ),

        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ),

        "Extra Trees": ExtraTreesClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ),

        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=3,
            random_state=42
        ),

        "MLP Neural Network": MLPClassifier(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            solver="adam",
            alpha=0.001,
            learning_rate_init=0.001,
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.2,
            random_state=42
        ),
    }


def train_models():
    print("Building training dataset...")

    df = build_training_dataset()
    X, y = prepare_features(df)

    if y.nunique() < 2:
        raise ValueError(
            "Target column only has one class. "
            "Model needs both delayed and not delayed records."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        stratify=y,
        random_state=42
    )

    models = get_models()

    results = []
    best_model = None
    best_model_name = None
    best_f1 = -1

    for model_name, model in models.items():
        print(f"\nTraining {model_name}...")

        pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("model", model)
            ]
        )

        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        results.append({
            "model": model_name,
            "accuracy": accuracy,
            "f1_score": f1
        })

        print(f"Accuracy: {accuracy:.4f}")
        print(f"F1 Score: {f1:.4f}")
        print("Confusion Matrix:")
        print(confusion_matrix(y_test, y_pred))
        print("Classification Report:")
        print(classification_report(y_test, y_pred, zero_division=0))

        if f1 > best_f1:
            best_f1 = f1
            best_model = pipeline
            best_model_name = model_name

    if best_model is None:
        raise RuntimeError("No model was trained successfully.")

    results_df = pd.DataFrame(results).sort_values(
        by="f1_score",
        ascending=False
    )

    print("\nModel Comparison:")
    print(results_df)

    joblib.dump(best_model, MODEL_PATH)

    print(f"\nBest model: {best_model_name}")
    print(f"Best F1 Score: {best_f1:.4f}")
    print(f"Saved model to: {MODEL_PATH}")

    return best_model, results_df


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No trained model found at {MODEL_PATH}. "
            "Run `python -m ml.train_model` first."
        )

    return joblib.load(MODEL_PATH)


def predict_delay(input_df):
    model = load_model()

    prediction = model.predict(input_df)

    prediction_probability = None
    if hasattr(model, "predict_proba"):
        prediction_probability = model.predict_proba(input_df)

    return prediction, prediction_probability


if __name__ == "__main__":
    train_models()