from django import template

register = template.Library()

@register.filter(name='rupiah')
def rupiah(value):
    """
    Mengubah angka integer menjadi format Rupiah.
    Contoh: 150000 -> Rp 150.000
    """
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value # Kembalikan aslinya jika bukan angka

    # Format angka dengan pemisah koma (standar internasional) -> 150,000
    formatted = f"{value:,}"
    
    # Ganti koma dengan titik (standar Indonesia) -> 150.000
    formatted = formatted.replace(",", ".")
    
    return f"Rp {formatted}"