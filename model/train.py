import os
import joblib
import numpy as np
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.linear_model import SGDClassifier
import json

OUT_DIR = os.environ.get("OUT_DIR", "./model_artifacts")
os.makedirs(OUT_DIR, exist_ok=True)

def main():
    data = load_iris()
    X, y = data.data, data.target
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    clf = SGDClassifier(random_state=42, max_iter=1000, tol=1e-3, loss="log_loss")
    clf.fit(X_train, y_train)
    acc = clf.score(X_test, y_test)
    print(f"Test accuracy: {acc:.4f}")

    joblib.dump(clf, os.path.join(OUT_DIR, "model.pkl"))
    np.save(os.path.join(OUT_DIR, "baseline.npy"), X_train)

    expectations = {
        "expectations": [
            {"expectation_type": "expect_table_row_count_to_be_between", "kwargs": {"min_value": 1}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": 0, "min_value": 0.0, "max_value": 8.0}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": 1, "min_value": 0.0, "max_value": 5.0}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": 2, "min_value": 0.0, "max_value": 8.0}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": 3, "min_value": 0.0, "max_value": 3.0}},
        ]
    }
    with open(os.path.join(OUT_DIR, "expectations.json"), "w") as f:
        json.dump(expectations, f)

if __name__ == "__main__":
    main()
