import json
import logging
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            obj = obj.tolist()
        elif isinstance(obj, np.int64):
            obj = int(obj)
        elif isinstance(obj, np.float64):
            obj = float(obj)

            return json.JSONEncoder.default(self, obj)

def jsonify(obj):
    try:
        return json.dumps(obj, cls=NumpyEncoder)
    except Exception as e:
        logging.exception("Error converting json, falling back on string")
        return str(obj)

