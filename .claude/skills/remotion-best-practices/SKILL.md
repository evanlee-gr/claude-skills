---
name: remotion-best-practices
description: Best practices for Remotion - Video creation in React
metadata:
  tags: remotion, video, react, animation, composition
---

## When to use

Use this skill whenever you are dealing with Remotion code to obtain the domain-specific knowledge.

## Remotion core concepts

* Use useCurrentFrame() to get the current frame number
* Use useVideoConfig() to get fps, width, height, durationInFrames
* Use interpolate() for smooth value transitions between frames
* Use spring() for physics-based animations
* Use Sequence to offset and trim child compositions
* Use Series for sequential compositions
* Use AbsoluteFill for full-canvas layers
* All animations are pure functions of the current frame - no side effects

## Performance

* Prefer CSS transforms over layout-affecting properties for animation
* Avoid heavy computations inside render - memoize with useMemo
* Use OffthreadVideo instead of Video for better render performance
* Keep compositions focused - split complex scenes into sub-compositions

## Captions and Subtitles

When dealing with captions or subtitles, use Remotion's built-in caption utilities. Ensure caption timing aligns with frame numbers using the fps from useVideoConfig().

## Using FFmpeg

For video operations such as trimming videos or detecting silence, FFmpeg should be used via @remotion/renderer or as a separate process.

## Silence Detection

When needing to detect and trim silent segments from video or audio files, use FFmpeg silencedetect filter or Remotion's audio utilities.

## Audio Visualization

For spectrum bars, waveforms, or bass-reactive effects, use Remotion's getAudioData() and visualizeAudio() utilities from @remotion/media-utils.

## Rendering

* Use npx remotion render for local rendering
* Use Remotion Lambda for cloud rendering at scale
* Always test with npx remotion preview before rendering
* Set durationInFrames explicitly on every composition