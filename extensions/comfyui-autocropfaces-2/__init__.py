import torch
import os
import numpy as np
import comfy.utils
from .Pytorch_Retinaface.pytorch_retinaface import Pytorch_RetinaFace
from comfy.model_management import get_torch_device

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    print("Warning: ultralytics not available. Head detection will not work.")

class AutoCropFaces:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "detection_model": (["face", "head"], {
                    "default": "face",
                    "tooltip": "Detection mode: 'face' uses RetinaFace for frontal/profile faces with visible features. 'head' uses YOLOv8 person detection to extract head regions, works for back of heads and any angle."
                }),
                "number_of_faces": ("INT", {
                    "default": 5,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "Maximum number of faces/heads to return. First selects the N largest faces by size, then orders them left-to-right, top-to-bottom."
                }),
                "reverse_order": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Reverse the face order. When enabled, faces are ordered right-to-left instead of left-to-right."
                }),
                "head_ratio": ("FLOAT", {
                    "default": 0.3,
                    "min": 0.1,
                    "max": 0.8,
                    "step": 0.05,
                    "display": "slider",
                    "tooltip": "For 'head' mode only: Portion of detected person height to use as head region. 0.3 = top 30% of person. Higher values include more of upper body."
                }),
                "scale_factor": ("FLOAT", {
                    "default": 1.5,
                    "min": 0.5,
                    "max": 10,
                    "step": 0.5,
                    "display": "slider",
                    "tooltip": "How much to scale/pad around detected face/head. 1.0 = exact detection size, 1.5 = 50% padding, higher values = more context around face/head."
                }),
                "shift_factor": ("FLOAT", {
                    "default": 0.45,
                    "min": 0,
                    "max": 1,
                    "step": 0.01,
                    "display": "slider",
                    "tooltip": "Vertical position of face/head in crop. 0.5 = centered, <0.5 = shift up (more space above), >0.5 = shift down (more space below). 0.45 works well for faces."
                }),
                "start_index": ("INT", {
                    "default": 0,
                    "step": 1,
                    "display": "number",
                    "tooltip": "Starting index for face selection. Useful for cycling through detected faces. Supports circular indexing (wraps around)."
                }),
                "max_faces_per_image": ("INT", {
                    "default": 50,
                    "min": 1,
                    "max": 1000,
                    "step": 1,
                    "tooltip": "Maximum faces to detect per image before filtering. Higher values slow down processing but catch more faces in crowded scenes."
                }),
                "confidence_threshold": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.01,
                    "max": 1.0,
                    "step": 0.01,
                    "display": "slider",
                    "tooltip": "Minimum confidence score for detection. Higher values (0.7-0.9) reduce false positives but may miss some faces. Lower values (0.3-0.5) detect more but may include non-faces."
                }),
                # "aspect_ratio": ("FLOAT", {
                #     "default": 1,
                #     "min": 0.2,
                #     "max": 5,
                #     "step": 0.1,
                # }),
                "aspect_ratio": (["9:16", "2:3", "3:4", "4:5", "1:1", "5:4", "4:3", "3:2", "16:9"], {
                    "default": "1:1",
                    "tooltip": "Aspect ratio for cropped output. 1:1 = square, 9:16 = portrait (tall), 16:9 = landscape (wide). Useful for specific output requirements."
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "CROP_DATA", "IMAGE", "IMAGE", "INT")
    RETURN_NAMES = ("face", "mask", "crop_data", "image_splited_1", "image_splited_2", "person_count")

    FUNCTION = "auto_crop_faces"

    CATEGORY = "Faces"

    def aspect_ratio_string_to_float(self, str_aspect_ratio="1:1"):
        a, b = map(float, str_aspect_ratio.split(':'))
        return a / b

    def detect_heads_from_people(self, image, head_ratio=0.3, confidence_threshold=0.5):
        """
        Detect people using YOLOv8 and extract head regions from top portion of person bboxes.
        Returns detections in format compatible with RetinaFace: [x1, y1, x2, y2, confidence]
        """
        if not ULTRALYTICS_AVAILABLE:
            print("Error: ultralytics not available for head detection")
            return np.array([])

        # Get ComfyUI base directory (3 levels up from this file)
        comfyui_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(comfyui_dir, "models", "ultralytics", "segm", "person_yolov8m-seg.pt")

        if not os.path.exists(model_path):
            print(f"Error: YOLOv8 model not found at {model_path}")
            return np.array([])

        # Load YOLOv8 model
        model = YOLO(model_path)

        # Convert tensor image to numpy for YOLO (expects HWC format, 0-255)
        if isinstance(image, torch.Tensor):
            image_np = (image.cpu().numpy() * 255).astype(np.uint8)
        else:
            image_np = (image * 255).astype(np.uint8)

        # Run detection
        results = model(image_np, conf=confidence_threshold, verbose=False)

        # Extract person bboxes and calculate head regions
        head_detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Get bbox coordinates and confidence
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()

                # Calculate head region (top portion of person bbox)
                person_height = y2 - y1
                head_height = person_height * head_ratio

                # Head bbox: same width, top portion of person
                head_x1 = x1
                head_x2 = x2
                head_y1 = y1
                head_y2 = y1 + head_height

                # Add to detections list [x1, y1, x2, y2, confidence]
                head_detections.append([head_x1, head_y1, head_x2, head_y2, conf])

        return np.array(head_detections)

    def create_face_mask(self, image_shape, bbox_info):
        """
        Create a binary mask for a face based on bounding box information.
        bbox_info is expected to be ((width, height), (x1, y1, x2, y2))
        Returns a mask tensor with shape (1, height, width) with values 0 or 1
        """
        height, width = image_shape[0], image_shape[1]
        mask = torch.zeros((height, width), dtype=torch.float32)

        # Unpack the bbox_info structure: ((width, height), (x1, y1, x2, y2))
        (face_w, face_h), (x1, y1, x2, y2) = bbox_info
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(width, int(x2))
        y2 = min(height, int(y2))

        mask[y1:y2, x1:x2] = 1.0

        return mask

    def adjust_split_position_for_divisibility(self, split_pos, total_size, divisor=4):
        """
        Adjust split position to ensure the first part has size divisible by the divisor.
        The second part takes the rest to maintain the original total size.
        Args:
            split_pos: Initial split position
            total_size: Total size of the dimension being split
            divisor: The divisor requirement (default: 4)
        Returns:
            Adjusted split position where first part is divisible by divisor
        """
        # Round down to nearest multiple of divisor to ensure first part is divisible
        adjusted_pos = (split_pos // divisor) * divisor

        # Ensure we have at least one divisor unit in the first part
        # and leave at least some pixels for the second part
        adjusted_pos = max(divisor, min(total_size - 1, adjusted_pos))

        return adjusted_pos

    def split_image_by_faces(self, image, crop_data_list):
        """
        Split an image into two parts based on face positions.
        Args:
            image: Input image tensor (batch, height, width, channels) or (height, width, channels)
            crop_data_list: List of crop data, each item is ((width, height), (x1, y1, x2, y2))
        Returns:
            image_splited_1, image_splited_2, person_count
        """
        # Handle empty or no faces case
        if not crop_data_list or len(crop_data_list) == 0:
            # No faces detected
            empty_image = torch.zeros_like(image)
            if len(image.shape) == 3:  # Single image (H, W, C)
                empty_image = empty_image.unsqueeze(0)
            elif len(image.shape) == 4:  # Batch (B, H, W, C)
                empty_image = empty_image[0:1]  # Take first image as empty template
            return empty_image, empty_image, 0

        # Handle single face case
        if len(crop_data_list) == 1:
            # One face detected - assign to image_splited_1
            if len(image.shape) == 3:
                img1 = image.unsqueeze(0)
            else:
                img1 = image
            empty_image = torch.zeros_like(img1)
            return img1, empty_image, 1

        # Two or more faces - split the image
        # Get the first two faces (already sorted by size and position)
        face1_info = crop_data_list[0]
        face2_info = crop_data_list[1]

        # Extract center positions
        (w1, h1), (x1_1, y1_1, x2_1, y2_1) = face1_info
        (w2, h2), (x1_2, y1_2, x2_2, y2_2) = face2_info

        center1_x = (x1_1 + x2_1) / 2
        center1_y = (y1_1 + y2_1) / 2
        center2_x = (x1_2 + x2_2) / 2
        center2_y = (y1_2 + y2_2) / 2

        # Calculate distances to determine split direction
        x_distance = abs(center1_x - center2_x)
        y_distance = abs(center1_y - center2_y)

        # Ensure image has batch dimension for processing
        if len(image.shape) == 3:
            image_batch = image.unsqueeze(0)
        else:
            image_batch = image

        # Get image dimensions (B, H, W, C)
        batch_size, img_height, img_width, channels = image_batch.shape

        # Determine split direction and calculate split position
        if x_distance > y_distance:
            # Split vertically (left/right)
            split_pos = int((center1_x + center2_x) / 2)
            split_pos = max(0, min(img_width, split_pos))

            # Determine which face is on the left (face1 should go to image_splited_1)
            face1_on_left = center1_x < center2_x

            if face1_on_left:
                # Face1 is on left, adjust split_pos so left part is divisible by 4
                split_pos = self.adjust_split_position_for_divisibility(split_pos, img_width, divisor=4)
                img_left = image_batch[:, :, :split_pos, :]
                img_right = image_batch[:, :, split_pos:, :]
                image_splited_1 = img_left
                image_splited_2 = img_right
            else:
                # Face1 is on right, adjust so right part is divisible by 4
                # Right part size = img_width - split_pos, we want this divisible by 4
                # So: (img_width - split_pos) % 4 == 0
                # Therefore: split_pos = img_width - (right_size rounded to divisible by 4)
                right_size = img_width - split_pos
                right_size_adjusted = (right_size // 4) * 4
                right_size_adjusted = max(4, min(img_width - 1, right_size_adjusted))
                split_pos = img_width - right_size_adjusted

                img_left = image_batch[:, :, :split_pos, :]
                img_right = image_batch[:, :, split_pos:, :]
                image_splited_1 = img_right
                image_splited_2 = img_left
        else:
            # Split horizontally (top/bottom)
            split_pos = int((center1_y + center2_y) / 2)
            split_pos = max(0, min(img_height, split_pos))

            # Determine which face is on top (face1 should go to image_splited_1)
            face1_on_top = center1_y < center2_y

            if face1_on_top:
                # Face1 is on top, adjust split_pos so top part is divisible by 4
                split_pos = self.adjust_split_position_for_divisibility(split_pos, img_height, divisor=4)
                img_top = image_batch[:, :split_pos, :, :]
                img_bottom = image_batch[:, split_pos:, :, :]
                image_splited_1 = img_top
                image_splited_2 = img_bottom
            else:
                # Face1 is on bottom, adjust so bottom part is divisible by 4
                # Bottom part size = img_height - split_pos, we want this divisible by 4
                # So: (img_height - split_pos) % 4 == 0
                # Therefore: split_pos = img_height - (bottom_size rounded to divisible by 4)
                bottom_size = img_height - split_pos
                bottom_size_adjusted = (bottom_size // 4) * 4
                bottom_size_adjusted = max(4, min(img_height - 1, bottom_size_adjusted))
                split_pos = img_height - bottom_size_adjusted

                img_top = image_batch[:, :split_pos, :, :]
                img_bottom = image_batch[:, split_pos:, :, :]
                image_splited_1 = img_bottom
                image_splited_2 = img_top

        return image_splited_1, image_splited_2, 2

    def auto_crop_faces_in_image (self, image, max_number_of_faces, scale_factor, shift_factor, aspect_ratio, confidence_threshold, detection_model="face", head_ratio=0.3, method='lanczos'):
        # Choose detection method based on model selection
        if detection_model == "head":
            # Use YOLOv8 person detection + head extraction
            dets = self.detect_heads_from_people(image, head_ratio=head_ratio, confidence_threshold=confidence_threshold)

            # Create a simple object to mimic RetinaFace for cropping
            class HeadDetector:
                def __init__(self, vis_thres):
                    self.vis_thres = vis_thres

                def center_and_crop_rescale(self, image, dets, scale_factor, shift_factor, aspect_ratio):
                    cropped_imgs = []
                    bbox_infos = []

                    import math
                    for bbox in dets:
                        if bbox[4] < self.vis_thres:
                            continue

                        x1, y1, x2, y2 = map(int, bbox[:4])
                        face_width = x2 - x1
                        face_height = y2 - y1

                        default_area = face_width * face_height
                        default_area *= scale_factor
                        default_side = math.sqrt(default_area)

                        new_face_width = int(default_side * math.sqrt(aspect_ratio))
                        new_face_height = int(default_side / math.sqrt(aspect_ratio))

                        center_x = x1 + face_width // 2
                        center_y = y1 + face_height // 2 + int(new_face_height * (0.5 - shift_factor))

                        original_crop_x1 = center_x - new_face_width // 2
                        original_crop_x2 = center_x + new_face_width // 2
                        original_crop_y1 = center_y - new_face_height // 2
                        original_crop_y2 = center_y + new_face_height // 2

                        crop_x1 = max(0, original_crop_x1)
                        crop_x2 = min(image.shape[1], original_crop_x2)
                        crop_y1 = max(0, original_crop_y1)
                        crop_y2 = min(image.shape[0], original_crop_y2)

                        cropped_imgs.append(image[crop_y1:crop_y2, crop_x1:crop_x2])
                        bbox_infos.append(((original_crop_x2-original_crop_x1, original_crop_y2-original_crop_y1),
                                         (original_crop_x1, original_crop_y1, original_crop_x2, original_crop_y2)))

                    return cropped_imgs, bbox_infos

            detector = HeadDetector(vis_thres=confidence_threshold)
            cropped_faces, bbox_info = detector.center_and_crop_rescale(image, dets, scale_factor=scale_factor, shift_factor=shift_factor, aspect_ratio=aspect_ratio)
        else:
            # Use RetinaFace for face detection
            image_255 = image * 255
            rf = Pytorch_RetinaFace(top_k=50, keep_top_k=max_number_of_faces, device=get_torch_device(), confidence_threshold=confidence_threshold)
            dets = rf.detect_faces(image_255)
            cropped_faces, bbox_info = rf.center_and_crop_rescale(image, dets, scale_factor=scale_factor, shift_factor=shift_factor, aspect_ratio=aspect_ratio)

        # Add a batch dimension to each cropped face
        cropped_faces_with_batch = [face.unsqueeze(0) for face in cropped_faces]

        # Create masks for each detected face
        masks = []
        for bbox in bbox_info:
            mask = self.create_face_mask(image.shape[:2], bbox)
            masks.append(mask)

        return cropped_faces_with_batch, masks, bbox_info

    def auto_crop_faces(self, image, detection_model, number_of_faces, reverse_order, head_ratio, start_index, max_faces_per_image, scale_factor, shift_factor, confidence_threshold, aspect_ratio, method='lanczos'):
        """
        "image" - Input can be one image or a batch of images with shape (batch, width, height, channel count)
        "detection_model" - "face" uses RetinaFace for face detection, "head" uses YOLOv8 person detection + head extraction
        "number_of_faces" - Maximum number of faces/heads to detect and return (ordered by position)
        "reverse_order" - If True, reverses face order to right-to-left instead of left-to-right
        "head_ratio" - For head detection mode: what portion (0.1-0.8) of person height to use as head region (0.3 = top 30%)
        "start_index" - The starting index of which face you select out of the set of detected faces.
        "scale_factor" - How much crop factor or padding do you want around each detected face.
        "shift_factor" - Pan up or down relative to the face, 0.5 should be right in the center.
        "confidence_threshold" - Minimum confidence score (0.01-1.0) for detection. Higher values reduce false positives.
        "aspect_ratio" - When we crop, you can have it crop down at a particular aspect ratio.
        "method" - Scaling pixel sampling interpolation method.
        """
        
        # Turn aspect ratio to float value
        aspect_ratio = self.aspect_ratio_string_to_float(aspect_ratio)

        selected_faces, detected_cropped_faces = [], []
        selected_crop_data, detected_crop_data = [], []
        selected_masks, detected_masks = [], []
        original_images = []

        # For split images - process per frame
        all_split_1 = []
        all_split_2 = []
        person_counts = []

        # Store first frame's split information to use for all frames
        first_frame_split_infos = None
        first_frame_person_count = 0

        # Loop through the input batches. Even if there is only one input image, it's still considered a batch.
        for i in range(image.shape[0]):

            original_images.append(image[i].unsqueeze(0)) # Temporarily the image, but insure it still has the batch dimension.
            # Detect the faces in the image, this will return multiple images and crop data for it.
            cropped_images, masks, infos = self.auto_crop_faces_in_image(
                image[i],
                max_faces_per_image,
                scale_factor,
                shift_factor,
                aspect_ratio,
                confidence_threshold,
                detection_model,
                head_ratio,
                method)

            detected_cropped_faces.extend(cropped_images)
            detected_masks.extend(masks)
            detected_crop_data.extend(infos)

            # Only process face detection for the FIRST frame to determine split info
            if i == 0:
                # Sort faces for the first frame: by size first, then by position
                if infos:
                    # Stage 1: Sort by size (area) to get largest faces
                    frame_face_sizes = [(info[0][0] * info[0][1], idx) for idx, info in enumerate(infos)]
                    largest_first = sorted(frame_face_sizes, reverse=True)

                    # Stage 2: Take top 2 (or fewer if less than 2 detected)
                    num_to_keep = min(2, len(largest_first))
                    largest_indices = [idx for _, idx in largest_first[:num_to_keep]]

                    # Stage 3: Sort those by position (left-to-right, top-to-bottom)
                    face_positions = []
                    for idx in largest_indices:
                        (_, _), (x1, y1, x2, y2) = infos[idx]
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        face_positions.append((center_x, center_y, idx))

                    sorted_indices = [idx for _, _, idx in sorted(face_positions)]

                    # Get the sorted infos for splitting (max 2 faces)
                    first_frame_split_infos = [infos[idx] for idx in sorted_indices]
                    first_frame_person_count = len(first_frame_split_infos)
                else:
                    first_frame_split_infos = []
                    first_frame_person_count = 0

            # Use the first frame's split info for ALL frames (including the first frame)
            split_1, split_2, p_count = self.split_image_by_faces(image[i], first_frame_split_infos)

            # Use the first frame's person count for all frames
            p_count = first_frame_person_count

            all_split_1.append(split_1)
            all_split_2.append(split_2)
            person_counts.append(p_count)

        # If we haven't detected anything, just return the original images, and default crop data.
        if not detected_cropped_faces or len(detected_cropped_faces) == 0:
            selected_crop_data = [(0, 0, img.shape[3], img.shape[2]) for img in original_images]
            # Create empty masks when no faces detected
            empty_mask = torch.zeros((image.shape[1], image.shape[2]), dtype=torch.float32)
            # Concatenate split images
            final_split_1 = torch.cat(all_split_1, dim=0) if all_split_1 else image
            final_split_2 = torch.cat(all_split_2, dim=0) if all_split_2 else torch.zeros_like(image)
            final_person_count = person_counts[0] if person_counts else 0
            return (image, empty_mask.unsqueeze(0), selected_crop_data, final_split_1, final_split_2, final_person_count)

        # Two-stage sorting:
        # 1. First, select the N largest faces by size (area)
        # 2. Then, order those N faces by position (left-to-right, top-to-bottom)
        # This ensures we get the largest faces, but ordered spatially for intuitive indexing
        # bbox_info structure: ((width, height), (x1, y1, x2, y2))

        # Stage 1: Sort by size to identify and select the largest faces
        face_sizes = [(bbox_info[0][0] * bbox_info[0][1], i) for i, bbox_info in enumerate(detected_crop_data)]
        largest_first = sorted(face_sizes, reverse=True)

        # Limit to number_of_faces (select only the largest N)
        num_to_keep = min(number_of_faces, len(largest_first))
        largest_indices = [i for _, i in largest_first[:num_to_keep]]

        # Stage 2: Sort the selected largest faces by position (left-to-right, top-to-bottom)
        face_positions = []
        for idx in largest_indices:
            bbox_info = detected_crop_data[idx]
            (width, height), (x1, y1, x2, y2) = bbox_info
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            # Sort by x first (left to right), then by y (top to bottom)
            face_positions.append((center_x, center_y, idx))

        sorted_indices = [i for _, _, i in sorted(face_positions)]

        # Apply reverse order if requested (right-to-left instead of left-to-right)
        if reverse_order:
            sorted_indices = sorted_indices[::-1]

        # Reorder all three lists based on sorted indices (now contains only largest N faces, position-ordered)
        detected_cropped_faces = [detected_cropped_faces[i] for i in sorted_indices]
        detected_masks = [detected_masks[i] for i in sorted_indices]
        detected_crop_data = [detected_crop_data[i] for i in sorted_indices]

        # Now detected_* lists contain the N largest faces ordered by position
        # start_index allows circular rotation through these faces
        start_index = start_index % len(detected_cropped_faces) if len(detected_cropped_faces) > 0 else 0

        # Apply circular rotation based on start_index
        selected_faces = detected_cropped_faces[start_index:] + detected_cropped_faces[:start_index]
        selected_masks = detected_masks[start_index:] + detected_masks[:start_index]
        selected_crop_data = detected_crop_data[start_index:] + detected_crop_data[:start_index]

        # If we haven't selected anything, then return original images.
        if len(selected_faces) == 0:
            # selected_crop_data = [(0, 0, img.shape[3], img.shape[2]) for img in original_images]
            empty_mask = torch.zeros((image.shape[1], image.shape[2]), dtype=torch.float32)
            # Concatenate split images
            final_split_1 = torch.cat(all_split_1, dim=0) if all_split_1 else image
            final_split_2 = torch.cat(all_split_2, dim=0) if all_split_2 else torch.zeros_like(image)
            final_person_count = person_counts[0] if person_counts else 0
            return (image, empty_mask.unsqueeze(0), None, final_split_1, final_split_2, final_person_count)

        # If there is only one detected face in batch of images, just return that one.
        elif len(selected_faces) <= 1:
            out = selected_faces[0]
            mask = selected_masks[0].unsqueeze(0)  # Add batch dimension
            crop_data = selected_crop_data[0] # to be compatible with WAS
            # Concatenate split images
            final_split_1 = torch.cat(all_split_1, dim=0) if all_split_1 else image
            final_split_2 = torch.cat(all_split_2, dim=0) if all_split_2 else torch.zeros_like(image)
            final_person_count = person_counts[0] if person_counts else 0
            return (out, mask, crop_data, final_split_1, final_split_2, final_person_count)

        # Determine the index of the face with the maximum width
        max_width_index = max(range(len(selected_faces)), key=lambda i: selected_faces[i].shape[1])

        # Determine the maximum width
        max_width = selected_faces[max_width_index].shape[1]
        max_height = selected_faces[max_width_index].shape[2]
        shape = (max_height, max_width)

        out = None
        out_masks = None
        # All images need to have the same width/height to fit into the tensor such that we can output as image batches.
        for i, face_image in enumerate(selected_faces):
            if shape != face_image.shape[1:3]: # Determine whether cropped face image size matches largest cropped face image.
                face_image = comfy.utils.common_upscale( # This method expects (batch, channel, height, width)
                    face_image.movedim(-1, 1), # Move channel dimension to width dimension
                    max_height, # Height
                    max_width, # Width
                    method, # Pixel sampling method.
                    "" # Only "center" is implemented right now, and we don't want to use that.
                ).movedim(1, -1)
            # Append the fitted image into the tensor.
            if out is None:
                out = face_image
            else:
                out = torch.cat((out, face_image), dim=0)

            # Batch the masks
            mask = selected_masks[i].unsqueeze(0)  # Add batch dimension
            if out_masks is None:
                out_masks = mask
            else:
                out_masks = torch.cat((out_masks, mask), dim=0)

        #TODO: WAS doesn't not support multiple faces, so this won't work with WAS.
        # Concatenate split images
        final_split_1 = torch.cat(all_split_1, dim=0) if all_split_1 else image
        final_split_2 = torch.cat(all_split_2, dim=0) if all_split_2 else torch.zeros_like(image)
        final_person_count = person_counts[0] if person_counts else 0
        return (out, out_masks, selected_crop_data, final_split_1, final_split_2, final_person_count)

NODE_CLASS_MAPPINGS = {
    "AutoCropFaces2": AutoCropFaces
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "AutoCropFaces2": "Auto Crop Faces 2"
}
