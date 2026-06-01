def priority_label_from_rank(rank):
    """Приоритет по числовому rank (очкам задачи или среднему rank команды)."""
    if rank > 600:
        return 'High'
    if rank > 300:
        return 'Medium'
    return 'Low'
