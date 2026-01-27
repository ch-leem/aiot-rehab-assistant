class AttentionHook:
    def __init__(self):
        self.att = None

    def __call__(self, module, inputs, output):
        # (B, C, H, W) → (B, H, W)
        self.att = output.abs().mean(dim=1)
