# distill/hooks.py

class AttentionMaskHook:
    def __init__(self):
        self.mask = None

    def __call__(self, module, inputs, output):
        self.mask = output.abs().mean(dim=1, keepdim=True)


class MultiScaleFeatureHook:
    def __init__(self):
        self.features = {}

    def clear(self):
        self.features.clear()


class NamedFeatureHook:
    """pickle 가능한 forward hook (클로저 금지)"""
    def __init__(self, container: MultiScaleFeatureHook, name: str):
        self.container = container
        self.name = name

    def __call__(self, module, inputs, output):
        self.container.features[self.name] = output
