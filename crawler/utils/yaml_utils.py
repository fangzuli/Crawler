import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config