"use client";

import { useEffect, useState } from "react";

/**
 * Custom hook to handle image loading with caching to prevent duplicate requests
 * Particularly useful for external images (like Google profile pictures) in React StrictMode
 */
export function useCachedImage(src: string | undefined) {
  const [imageStatus, setImageStatus] = useState<
    "loading" | "loaded" | "error"
  >("loading");
  const [imageSrc, setImageSrc] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!src) {
      setImageStatus("error");
      return;
    }

    let isCancelled = false;

    // Check if image is already cached in browser
    const img = new Image();

    const handleLoad = () => {
      if (!isCancelled) {
        setImageSrc(src);
        setImageStatus("loaded");
      }
    };

    const handleError = () => {
      if (!isCancelled) {
        setImageStatus("error");
      }
    };

    img.onload = handleLoad;
    img.onerror = handleError;

    // Start loading the image
    img.src = src;

    // If image is already cached, it will fire load event immediately
    if (img.complete && img.naturalHeight !== 0) {
      handleLoad();
    }

    // Cleanup function to prevent state updates on unmounted component
    return () => {
      isCancelled = true;
      img.onload = null;
      img.onerror = null;
    };
  }, [src]);

  return { imageSrc, imageStatus };
}
