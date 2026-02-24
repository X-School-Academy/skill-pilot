Update AutoCropFaces node to add 3 new outputs: `image_splited_1`, `image_splited_2`, person_count: 0, 1 or 2

For a video, which may have two heads/faces, the location can be left, right or top, bottom, we need to split the frame/image to two frames/images, left, right or top, bottom.

we should split the frame from the middle line of two heads/faces. auto detect it should split in horizoanl or vertical direction depending on the face/head relative location x, or y which is large

if no face, set person_count to 0
if 1 face, set person_count to 1, and the image to image_splited_1
if 2 face, set person_count to 2, and the split image to image_splited_1 and image_splited_2
if more than 2 faces, just return the largest 2 faces (using current face order)
for each frame, the first face related image part in the face order, should assign to image_splited_1

we will assume the face not change location in all the video. so only use the first frame's face information to split the frames to make sure all frames should have same size.

we can merge image_splited_1 and image_splited_2 into a whole video

- image_splited_1 (containing the first face) will always have dimensions divisible by 4 ✓
- image_splited_2 takes the remaining part ✓
- When merged together, they equal the original frame size ✓