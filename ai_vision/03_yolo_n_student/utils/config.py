import yaml
'''
yaml 로딩
'''
def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)
