#!/usr/bin/env python3
"""
shrink_images.py — aggressive Y-mode first (lossy-first when user asks Y)

Behavior:
- If user selects Y (force_all_to_webp=True):
    * All files are converted to WebP.
    * For files > MIN_TRIGGER_SIZE (1.5MB), we prefer resizing + lossy WebP (no lossless first).
- If user selects N: previous behavior (PNG/JPG always convert; WEBP/AVIF shrink only if > threshold).
- HEIC/HEIF support via pillow_heif if available; macOS sips fallback if not.
"""
import os
import sys
import subprocess
import tempfile
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Optional plugin flags
try:
    import pillow_avif  # noqa: F401
    AVIF_AVAILABLE = True
except Exception:
    AVIF_AVAILABLE = False

HEIF_AVAILABLE = False
try:
    import pillow_heif  # noqa: F401
    try:
        pillow_heif.register_heif_opener()
    except Exception:
        pass
    HEIF_AVAILABLE = True
except Exception:
    HEIF_AVAILABLE = False

# Settings
MAX_FINAL_SIZE = 800 * 1024             # 600 KB
MIN_TRIGGER_SIZE = int(1.5 * 1024 * 1024)  # 1.5 MB
SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".avif", ".heic", ".heif")

# Resize settings — enabled when force_shrink is True and original > MIN_TRIGGER_SIZE
ENABLE_RESIZE_FOR_LARGE = True
MAX_WIDTH_FOR_RESIZE = 1920

def bytesize(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0

def try_save_lossless_webp(img, out_path):
    img.save(out_path, format="WEBP", lossless=True, method=6)

def try_save_lossy_webp(img, out_path, quality):
    img.save(out_path, format="WEBP", quality=quality, method=6)

def try_save_optimized_jpeg(img, out_path, quality):
    img.convert("RGB").save(out_path, format="JPEG", optimize=True, quality=quality)

def open_image_with_fallback(input_path):
    """
    Try PIL.Image.open; if that fails for HEIC/HEIF and pillow_heif not installed,
    on macOS use sips to create a temp JPEG and open that.
    Returns (Image object, temp_file_path_or_None) - temp_file_path must be cleaned by caller if present.
    """
    temp_file = None
    try:
        img = Image.open(input_path)
        return img, None
    except Exception as e:
        ext = os.path.splitext(input_path)[1].lower()
        if ext in (".heic", ".heif") and not HEIF_AVAILABLE and sys.platform == "darwin":
            try:
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                tmp_jpeg = tmp.name
                tmp.close()
                subprocess.check_call(["sips", "-s", "format", "jpeg", input_path, "--out", tmp_jpeg],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                img = Image.open(tmp_jpeg)
                return img, tmp_jpeg
            except Exception as s_e:
                # cleanup and re-raise original error
                try:
                    if 'tmp_jpeg' in locals() and os.path.exists(tmp_jpeg):
                        os.remove(tmp_jpeg)
                except Exception:
                    pass
                raise e
        else:
            raise

def resize_if_needed(img, max_width):
    if img.width > max_width:
        new_h = int(max_width / img.width * img.height)
        return img.resize((max_width, new_h), Image.LANCZOS)
    return img

def shrink_and_convert(input_path, output_path, force_shrink=False):
    basename = os.path.basename(input_path)
    original_size = bytesize(input_path)
    ext = os.path.splitext(input_path)[1].lower()

    # Open with fallback (returns a temp file path if used)
    try:
        img, tmp_file = open_image_with_fallback(input_path)
    except Exception as e:
        print(f"⚠️ Could not open {basename}: {e}")
        return
    # tmp_file (if any) will be removed at the end

    if ext == ".avif" and not AVIF_AVAILABLE:
        print(f"⚠️ AVIF support not installed; attempting to process {basename} anyway (may fail).")

    # Decide shrink policy
    if force_shrink:
        # Y mode: convert ALL files, and for large files, aggressively attempt to shrink.
        should_try_shrink = original_size > MIN_TRIGGER_SIZE
        prefer_lossy_first = True   # force lossy-first in Y mode (strict)
    else:
        # N mode: older behavior
        if ext in (".png", ".jpg", ".jpeg"):
            should_try_shrink = False
        elif ext in (".webp", ".avif"):
            should_try_shrink = original_size > MIN_TRIGGER_SIZE
        elif ext in (".heic", ".heif"):
            should_try_shrink = False
        else:
            should_try_shrink = False
        prefer_lossy_first = False

    # If prefer_lossy_first, we skip lossless attempt for large files
    if not prefer_lossy_first:
        # Try lossless (good for small originals)
        try:
            try_save_lossless_webp(img, output_path)
            out_size = bytesize(output_path)
            if not should_try_shrink or out_size <= MAX_FINAL_SIZE:
                print(f"{basename} → converted to WebP (lossless) {out_size/1024:.1f} KB")
                # cleanup tmp file if any
                if tmp_file:
                    try: os.remove(tmp_file)
                    except Exception: pass
                return
        except Exception as e:
            print(f"⚠️ Lossless WebP save failed for {basename}: {e}")

    # From here we will attempt lossy compression (either because prefer_lossy_first or lossless didn't meet target)
    # Re-open original to avoid writing-over artifacts; use fallback again:
    try:
        img, extra_tmp = open_image_with_fallback(input_path)
        if extra_tmp and not tmp_file:
            tmp_file = extra_tmp
    except Exception as e:
        print(f"⚠️ Re-open failed for {basename}: {e}")
        if tmp_file:
            try: os.remove(tmp_file)
            except Exception: pass
        return

    # Optionally resize if large and in force_shrink mode
    if force_shrink and should_try_shrink and ENABLE_RESIZE_FOR_LARGE:
        img = resize_if_needed(img, MAX_WIDTH_FOR_RESIZE)

    # Lossy quality ladder (aggressive: down to q=40)
    lossy_qualities = [95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40]
    shrunk = False
    for q in lossy_qualities:
        try:
            # Re-open again to avoid accumulating changes if using tmp fallback
            try:
                img_iter, extra_tmp2 = open_image_with_fallback(input_path)
                if extra_tmp2 and not tmp_file:
                    tmp_file = extra_tmp2
                # apply resize again if needed
                if force_shrink and should_try_shrink and ENABLE_RESIZE_FOR_LARGE:
                    img_iter = resize_if_needed(img_iter, MAX_WIDTH_FOR_RESIZE)
                try_save_lossy_webp(img_iter, output_path, quality=q)
            except Exception:
                # as a fallback, try using the previously loaded img variable (if available)
                try:
                    try_save_lossy_webp(img, output_path, quality=q)
                except Exception:
                    continue

            out_size = bytesize(output_path)
            if out_size <= MAX_FINAL_SIZE:
                print(f"{basename} → lossy WebP q={q} {out_size/1024:.1f} KB (target met)")
                shrunk = True
                break
            else:
                print(f"{basename} → lossy WebP q={q} produced {out_size/1024:.1f} KB (still >target)")
        except Exception:
            continue

    if shrunk:
        if tmp_file:
            try: os.remove(tmp_file)
            except Exception: pass
        return

    # JPEG fallback (lose alpha) -> then convert to webp
    jpeg_qualities = [85, 80, 75, 70, 65]
    jpeg_temp = os.path.splitext(output_path)[0] + "_jpeg_fallback.jpg"
    for q in jpeg_qualities:
        try:
            # open and convert to RGB
            img_rgb, extra_tmp3 = open_image_with_fallback(input_path)
            if extra_tmp3 and not tmp_file:
                tmp_file = extra_tmp3
            img_rgb = img_rgb.convert("RGB")
            # apply resize if needed
            if force_shrink and should_try_shrink and ENABLE_RESIZE_FOR_LARGE:
                img_rgb = resize_if_needed(img_rgb, MAX_WIDTH_FOR_RESIZE)
            try_save_optimized_jpeg(img_rgb, jpeg_temp, quality=q)
            jsize = bytesize(jpeg_temp)
            if jsize <= MAX_FINAL_SIZE:
                # convert jpeg -> webp
                with Image.open(jpeg_temp) as jimg:
                    try_save_lossy_webp(jimg, output_path, quality=95)
                out_size = bytesize(output_path)
                try:
                    os.remove(jpeg_temp)
                except Exception:
                    pass
                if out_size <= MAX_FINAL_SIZE:
                    print(f"{basename} → JPEG fallback q={q} → WebP {out_size/1024:.1f} KB (target met)")
                    if tmp_file:
                        try: os.remove(tmp_file)
                        except Exception: pass
                    return
        except Exception:
            continue
        finally:
            if os.path.exists(jpeg_temp):
                try: os.remove(jpeg_temp)
                except Exception: pass

    # If we get here, best-effort failed to reach target
    final_size = bytesize(output_path)
    if final_size > 0:
        print(f"{basename} → could not reach {MAX_FINAL_SIZE/1024:.1f}KB; final size {final_size/1024:.1f} KB (best-effort)")
    else:
        print(f"{basename} → processing failed, no output produced.")
    if tmp_file:
        try: os.remove(tmp_file)
        except Exception: pass

def process_folder(folder_path, force_all_to_webp=False):
    output_folder = os.path.join(folder_path, "shrinked_images")
    os.makedirs(output_folder, exist_ok=True)

    files = [f for f in os.listdir(folder_path) if f.lower().endswith(SUPPORTED_EXTS)]
    total = len(files)
    if total == 0:
        print("No supported image files found in the folder.")
        return

    print(f"Found {total} image(s). Processing...")

    try:
        for i, fname in enumerate(files, start=1):
            in_path = os.path.join(folder_path, fname)
            name, _ = os.path.splitext(fname)
            out_path = os.path.join(output_folder, name + ".webp")
            print(f"[{i}/{total}] {fname} ...")
            shrink_and_convert(in_path, out_path, force_shrink=force_all_to_webp)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
        return

    print(f"\n✅ Done. Output folder: {output_folder}")

def prompt_folder():
    while True:
        folder = input("📂 Enter the folder path containing images: ").strip()
        if os.path.isdir(folder):
            return folder
        print("❌ Invalid folder path! Please try again.\n")

def prompt_yes_no(prompt_text):
    while True:
        c = input(prompt_text + " (y/n): ").strip().lower()
        if c in ("y", "n"):
            return c == "y"
        print("Please enter 'y' or 'n'.")

if __name__ == "__main__":
    folder = prompt_folder()
    print("\n🔄 Choose mode:")
    print(" Y = Convert ALL files to WebP AND for files >1.5MB try to shrink to <600KB (best-effort).")
    print(" N = Convert PNG/JPG to WebP always; only process WEBP/AVIF if >1.5MB (existing behavior).")
    force = prompt_yes_no("Do you want to convert ALL files to WebP and shrink large ones if needed?")
    process_folder(folder, force_all_to_webp=force)
