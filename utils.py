# === utils.py ===

def create_progress_bar(percentage):
    total_blocks = 10
    filled_blocks = int((percentage / 100) * total_blocks)
    return '█' * filled_blocks + '-' * (total_blocks - filled_blocks)