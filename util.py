import json
import logging
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.int64):
            return int(obj)
        elif isinstance(obj, np.float64):
            return float(obj)
        try:
            return json.JSONEncoder.default(self, obj)
        except Exception as e:
            logging.warning("Couldn't convert %s to json; falling back on string ", obj)
            return str(obj)


def jsonify(obj):
    try:
        return json.dumps(obj, cls=NumpyEncoder)
    except Exception as e:
        logging.exception("Error converting json, falling back on string")
        return str(obj)


if __name__ == '__main__':
    print(jsonify({
        "x": np.array([1,2,3]),
        "y": np.array([1,2,3])[0]
    }))