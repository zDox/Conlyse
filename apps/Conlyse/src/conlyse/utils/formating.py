def format_bytes(bytes_val):
    if bytes_val == 0:
        return '0 Bytes'
    k = 1024
    sizes = ['Bytes', 'KB', 'MB', 'GB']
    i = int(len(bin(bytes_val)) - len(bin(k))) // 10
    if i >= len(sizes):
        i = len(sizes) - 1
    return f"{round(bytes_val / (k ** i), 2)} {sizes[i]}"

def format_date(date):
    return date.strftime('%b %d, %Y %I:%M %p')
