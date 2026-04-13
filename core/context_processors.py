from django.utils import translation
from .utils import is_rtl_language

def translation_context(request):
    current_lang = translation.get_language()
    return {
        'LANGUAGE_CODE': current_lang,
        'LANGUAGE_BIDI': is_rtl_language(current_lang),
    }