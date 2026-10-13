
from flask import Flask,request,jsonify
from pathlib import Path

import json
import logging
import os

import numpy as np
import cloudpickle

from preprocessor import preprocess


BASE_DIR=Path(__file__).resolve().parent


CONFIG=json.loads(
    (
        BASE_DIR/
        "backend_config.json"
    ).read_text(
        encoding="utf-8"
    )
)


BUNDLE_PATH=(
    BASE_DIR/
    CONFIG["bundle_file"]
)


with BUNDLE_PATH.open("rb") as f:
    BUNDLE=cloudpickle.load(f)


PIPELINE=BUNDLE[
    "pipeline"
]


METADATA=BUNDLE.get(
    "metadata",
    {}
)


MODEL_VERSION=str(
    METADATA.get(
        "model_version",
        CONFIG[
            "model_version"
        ]
    )
)


raw_class_map=METADATA.get(
    "class_mapping",
    {
        "0":"Non-Disaster",
        "1":"Disaster"
    }
)


if isinstance(raw_class_map,dict):
    CLASS_MAP={
        int(k):str(v)
        for k,v
        in raw_class_map.items()
    }
else:
    CLASS_MAP={
        0:"Non-Disaster",
        1:"Disaster"
    }


app=Flask(__name__)


app.config[
    "MAX_CONTENT_LENGTH"
]=int(
    CONFIG[
        "max_request_bytes"
    ]
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    )
)


logger=logging.getLogger(
    "disaster_tweet_api"
)


logger.info(
    "Backend initialized | model_version=%s",
    MODEL_VERSION
)


def model_predict(text):

    row=preprocess(
        text
    )

    pred=int(
        PIPELINE.predict(
            row
        )[0]
    )

    result={
        "prediction":pred,
        "label":CLASS_MAP.get(
            pred,
            str(pred)
        ),
        "model_version":MODEL_VERSION
    }

    if hasattr(
        PIPELINE,
        "predict_proba"
    ):

        probabilities=np.asarray(
            PIPELINE.predict_proba(
                row
            )
        )[0]

        classes=np.asarray(
            getattr(
                PIPELINE,
                "classes_",
                range(
                    len(
                        probabilities
                    )
                )
            )
        )

        indexes=np.where(
            classes==pred
        )[0]

        idx=(
            int(indexes[0])
            if len(indexes)
            else int(
                np.argmax(
                    probabilities
                )
            )
        )

        result["score"]=float(
            probabilities[idx]
        )

        result[
            "score_type"
        ]="Probability"

    elif hasattr(
        PIPELINE,
        "decision_function"
    ):

        score=float(
            np.asarray(
                PIPELINE.decision_function(
                    row
                )
            ).reshape(-1)[0]
        )

        result["score"]=score
        result[
            "score_type"
        ]="Decision Score"

    else:

        result["score"]=None
        result[
            "score_type"
        ]="Class Only"

    return result


@app.get("/")
def service_info():

    return jsonify({
        "service":
            CONFIG[
                "service_name"
            ],

        "model_version":
            MODEL_VERSION,

        "status":
            "available",

        "endpoints":{
            "health":
                "GET /health",

            "predict":
                "POST /predict"
        }
    })


@app.get("/health")
def health():

    return jsonify({
        "status":"healthy",
        "model_loaded":True,
        "model_version":MODEL_VERSION
    })


@app.post("/predict")
def predict():

    if not request.is_json:

        return jsonify({
            "status":"error",
            "message":
                "Request body must be JSON."
        }),415

    payload=request.get_json(
        silent=True
    )

    if not isinstance(
        payload,
        dict
    ):

        return jsonify({
            "status":"error",
            "message":
                "Invalid JSON payload."
        }),400

    if "text" not in payload:

        return jsonify({
            "status":"error",
            "message":
                "Required field 'text' is missing."
        }),400

    try:

        result=model_predict(
            payload[
                "text"
            ]
        )

        return jsonify({
            "status":"success",
            **result
        }),200

    except (
        TypeError,
        ValueError
    ) as e:

        return jsonify({
            "status":"error",
            "message":str(e)
        }),400

    except Exception:

        logger.exception(
            "Prediction request failed"
        )

        return jsonify({
            "status":"error",
            "message":
                "Prediction service encountered an internal error."
        }),500


@app.errorhandler(413)
def request_too_large(_):

    return jsonify({
        "status":"error",
        "message":
            "Request payload is too large."
    }),413


@app.errorhandler(404)
def not_found(_):

    return jsonify({
        "status":"error",
        "message":
            "Endpoint not found."
    }),404


if __name__=="__main__":

    app.run(
        host=os.getenv(
            "HOST",
            "127.0.0.1"
        ),
        port=int(
            os.getenv(
                "PORT",
                "5000"
            )
        ),
        debug=False
    )
