def is_rtl_language(lang_code):
    """Utility to check if the current language requires RTL layout."""
    base_lang = lang_code.split('-')[0] if lang_code else 'en'
    return base_lang in ['fa', 'ps']