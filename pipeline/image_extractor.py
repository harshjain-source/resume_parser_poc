import os
import fitz  # PyMuPDF
from PIL import Image
import cv2
import shutil

class ImageExtractor:
    """
    Stage 1.5: Image Extraction & Filtering.
    Extracts images from the first two pages and identifies the candidate photo
    using aspect ratio and face detection.
    """
    def __init__(self, resume_id: str, output_dir: str):
        self.resume_id = resume_id
        self.output_dir = os.path.join(output_dir, "photo")
        # Load face cascade once
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def _contains_face(self, image_path: str) -> bool:
        """Checks if an image contains at least one face."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            return len(faces) > 0
        except Exception as e:
            print(f"Face detection error: {e}")
            return False

    def run(self, pdf_path: str) -> str:
        """
        Extracts and filters images to find the candidate's portrait.
        Returns the path to the best candidate photo, or None.
        """
        if not os.path.exists(pdf_path):
            return None

        # Clean/Prepare photo directory
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return None

        # Process first and second page
        best_photo_path = None
        num_pages = min(2, len(doc))

        for page_index in range(num_pages):
            page = doc[page_index]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]

                # Use page_index in filename to avoid collisions
                temp_path = os.path.join(self.output_dir, f"temp_p{page_index}_{img_index}.{ext}")
                with open(temp_path, "wb") as f:
                    f.write(image_bytes)

                # Filtering logic
                is_valid = False
                try:
                    with Image.open(temp_path) as pil_img:
                        w, h = pil_img.size
                    
                    ratio = w / h
                    # Passport size/Portrait filters
                    if w > 60 and h > 80 and 0.5 < ratio < 0.95:
                        if self._contains_face(temp_path):
                            is_valid = True
                except Exception:
                    is_valid = False

                if is_valid and not best_photo_path:
                    # Rename to a permanent name
                    final_path = os.path.join(self.output_dir, f"candidate_photo.{ext}")
                    os.rename(temp_path, final_path)
                    best_photo_path = final_path
                    # We found the best candidate, but we keep cleaning up other images
                else:
                    # Cleanup if not valid or if we already found the best one
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            
            if best_photo_path:
                break # Stop searching subsequent pages if photo found on earlier page

        doc.close()
        
        # Return relative path for JSON/UI portability
        if best_photo_path:
            return os.path.join("photo", os.path.basename(best_photo_path))
        return None
