import base64
import io
import random
import string
import time
from threading import Lock

from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.cache import cache


_fallback_cache = {}
_fallback_lock = Lock()


def _fallback_set(key, value, timeout):
    expire_at = time.time() + timeout if timeout else None
    with _fallback_lock:
        _fallback_cache[key] = (value, expire_at)


def _fallback_get(key):
    with _fallback_lock:
        item = _fallback_cache.get(key)
        if not item:
            return None
        value, expire_at = item
        if expire_at and expire_at < time.time():
            _fallback_cache.pop(key, None)
            return None
        return value


def _fallback_delete(key):
    with _fallback_lock:
        _fallback_cache.pop(key, None)


def cache_set(key, value, timeout):
    try:
        cache.set(key, value, timeout=timeout)
        return
    except Exception:
        pass
    _fallback_set(key, value, timeout)


def cache_get(key):
    try:
        value = cache.get(key)
        if value is not None:
            return value
    except Exception:
        pass
    return _fallback_get(key)


def cache_delete(key):
    try:
        cache.delete(key)
    except Exception:
        pass
    _fallback_delete(key)


def generate_captcha_code(length=4):
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(random.choices(chars, k=length))


def _load_captcha_font():
    """
    Use Pillow's built-in bitmap font to avoid environment-specific tofu glyphs.
    In this runtime, several truetype fonts render ASCII as square boxes.
    """
    return ImageFont.load_default()


def _draw_scaled_default_char(image, char, x, y, color, scale=3):
    # Draw char on a tiny mask with default font, then upscale for readability.
    mask = Image.new('L', (20, 20), 0)
    mask_draw = ImageDraw.Draw(mask)
    font = ImageFont.load_default()
    mask_draw.text((0, 0), char, font=font, fill=255)
    bbox = mask.getbbox()
    if not bbox:
        return
    glyph = mask.crop(bbox).resize((18 * scale // 2, 22 * scale // 2), Image.Resampling.NEAREST)
    rgba = Image.new('RGBA', glyph.size, color + (255,))
    image.paste(rgba, (int(x), int(y)), glyph)


def generate_captcha_image(code, width=160, height=60):
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    for _ in range(80):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(200, 240), random.randint(200, 240), random.randint(200, 240)))

    for _ in range(2):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(180, 220), random.randint(180, 220), random.randint(180, 220)), width=1)

    font = _load_captcha_font()

    char_count = len(code)
    total_width = width * 0.8
    start_x = (width - total_width) / 2
    spacing = total_width / char_count

    for i, char in enumerate(code):
        x = start_x + spacing * i + spacing / 4 + random.randint(-5, 5)
        y = 10 + random.randint(-2, 2)
        color = (random.randint(20, 80), random.randint(20, 80), random.randint(20, 80))

        _draw_scaled_default_char(image, char, x + 2, y + 2, (180, 180, 180), scale=3)
        _draw_scaled_default_char(image, char, x, y, color, scale=3)

    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=(180, 180, 180), width=2)

    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f'data:image/png;base64,{image_base64}'


def create_captcha(captcha_id=None):
    if not captcha_id:
        captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    code = generate_captcha_code()
    image_data = generate_captcha_image(code)

    cache_key = f'captcha:{captcha_id}'
    cache_set(cache_key, code.lower(), timeout=300)

    return {'captcha_id': captcha_id, 'captcha_image': image_data}


def verify_captcha(captcha_id, code):
    if not captcha_id or not code:
        return False

    cache_key = f'captcha:{captcha_id}'
    stored_code = cache_get(cache_key)
    if not stored_code:
        return False

    if stored_code == code.lower():
        cache_delete(cache_key)
        return True

    return False


def generate_email_code(length=6):
    return ''.join(random.choices(string.digits, k=length))


def send_email_code(email, code_type='register'):
    from django.core.mail import send_mail

    code = generate_email_code()
    cache_key = f'email_code:{code_type}:{email}'
    cache_set(cache_key, code, timeout=600)

    if code_type == 'register':
        subject = '玩偶商城 - 注册验证码'
        message = f'您的验证码是：{code}，有效期10分钟。'
    elif code_type == 'forgot':
        subject = '玩偶商城 - 密码重置验证码'
        message = f'您的验证码是：{code}，有效期10分钟。'
    else:
        subject = '玩偶商城 - 验证码'
        message = f'您的验证码是：{code}，有效期10分钟。'

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[email],
            fail_silently=False,
        )
        return {'ok': True, 'code': code, 'error': ''}
    except Exception as exc:
        import traceback
        error_detail = f"{str(exc)}\n{traceback.format_exc()}"
        print(f"[EMAIL ERROR] {error_detail}")
        return {'ok': False, 'code': code, 'error': str(exc)}


def verify_email_code(email, code, code_type='register'):
    if not email or not code:
        return False

    cache_key = f'email_code:{code_type}:{email}'
    stored_code = cache_get(cache_key)
    if not stored_code:
        return False

    if stored_code == code:
        cache_delete(cache_key)
        return True

    return False


def send_verification_email(email, subject, message):
    from django.core.mail import send_mail

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception:
        return False
