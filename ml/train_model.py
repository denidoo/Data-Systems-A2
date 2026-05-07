import joblib
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.feature_engineering import (
    build_training_dataset,
    prepare_features,
    get_feature_columns
)


MODEL_DIR = Path("ml/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "delay_model.pkl"


def build_preprocessor():
    numeric_features, categorical_features = get_feature_columns()

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore"))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, numeric_features),
            ("categorical", categorical_transformer, categorical_features)
        ]
    )

    return preprocessor


def evaluate_model(name, model, X_test, y_test):
    y_pred = model.predict(X_test)

    results = {
        "model": name,
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0)
    }

    print(f"\n{name} Results")
    print("-" * 40)
    print(f"Accuracy:  {results['accuracy']:.4f}")
    print(f"Precision: {results['precision']:.4f}")
    print(f"Recall:    {results['recall']:.4f}")
    print(f"F1-score:  {results['f1']:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    return results


def train_models():
    print("Loading processed training data...")
    df = build_training_dataset()

    print(f"Training dataset rows: {len(df)}")

    X, y = prepare_features(df)

    if y.nunique() < 2:
        raise ValueError(
            "The target column only has one class. "
            "You need both delayed and on-time flights to train a classifier."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    preprocessor = build_preprocessor()

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Random Forest": RandomForestClassifier(
            n_estimators=150,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1
        ),
        "Hist Gradient Boosting": HistGradientBoostingClassifier(
            random_state=42,
            max_iter=150
        )
    }

    trained_models = {}
    results = []

    for name, classifier in models.items():
        print(f"\nTraining {name}...")

        pipeline = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier)
        ])

        pipeline.fit(X_train, y_train)

        result = evaluate_model(name, pipeline, X_test, y_test)

        trained_models[name] = pipeline
        results.append(result)

    best_result = max(results, key=lambda item: item["f1"])
    best_model_name = best_result["model"]
    best_model = trained_models[best_model_name]

    joblib.dump(best_model, MODEL_PATH)

    print("\nBest model selected:")
    print(best_model_name)
    print(f"Saved to: {MODEL_PATH}")

    return best_model


if __name__ == "__main__":
    train_models()