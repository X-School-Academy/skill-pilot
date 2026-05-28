# Xiaohongshu (小红书) Platform Guide

## UI Navigation & Elements
- **Creator Center URL**: `https://creator.xiaohongshu.com/publish/publish`
- **Publish Page**:
  - **Image/Video Upload**: Role `button` or `input[type="file"]`, text "上传图片" or "上传视频". Note: Drag-and-drop usually works.
  - **Title Box**: Input labeled "填写标题". Max 20 characters recommended.
  - **Content Textarea**: Role `textbox`, usually the largest input area.
  - **Publish Button**: Button with text "发布" (Publish).

## Posting Strategy

### Primary Format: Image Slides + Caption

Xiaohongshu is an **image-first platform**. The dominant format is 1-9 image slides with styled text overlays, supported by a short caption. Pure text posts significantly underperform.

### Image Slide Specifications

- **Count**: 1-9 slides. 3-6 is the sweet spot for educational/how-to content.
- **Slide 1 — Title Card**: The hook. Big bold text. Eye-catching. Could be a question, a bold claim, or a number. Often uses 【brackets】 or emojis.
- **Slides 2 to N-1 — Content**: One key point per slide. Title line (larger) + 2-3 lines of supporting detail (smaller). Leave breathing room.
- **Last Slide — Close**: Summary, CTA, or your handle/contact.
- **Background**: Gradient, solid aesthetic color, or high-quality photo. Never plain white — it looks unfinished.
- **Typography**: Large enough to read on a phone without zooming. One font family throughout for consistency.
- **Aspect Ratio**: 3:4 vertical (standard for XHS feed).

### Caption (笔记文字)

- **Length**: 50-150 characters. The images carry the weight; the caption provides context.
- **Opening**: Context or personal note. Don't repeat the title card verbatim.
- **Body**: 1-3 short sentences. Colloquial tone.
- **Tags**: 5-10 hashtags at the very end.
- **Emojis**: Expected and natural. Don't force one per line.

### Content Strategy

- **Visuals**: Mandatory. High-quality, aesthetic images perform best.
- **Title**: Use brackets like 【...】 or emojis to stand out. Max 20 chars.
- **Body**: Use emojis naturally. Keep it helpful (干货). Personal experience > general advice.
- **Tags**: 5-10 tags starting with # at the very end of the content.
- **Voice**: Colloquial Chinese. Like sharing tips with a friend. See `social-content` skill for full Chinese anti-AI writing rules.

### Image Generation Workflow

When creating XHS posts, generate images with text overlay programmatically:
1. Write the slide content (title + body per slide) following Chinese anti-AI rules
2. Render each slide as an image with styled text on a gradient/aesthetic background
3. Upload images to XHS creator center
4. Add the caption and publish

A helper script at `.skillpilot/temp/render-xhs-slides.py` can generate slide images from content.
