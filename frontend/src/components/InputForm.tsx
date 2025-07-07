import {
  Dispatch,
  FormEventHandler,
  KeyboardEventHandler,
  SetStateAction,
  useState,
  useRef,
} from "react";

import UpArrow from "@/icons/UpArrow";
import PlusIcon from "@/icons/PlusIcon";

interface Props {
  onSubmit: FormEventHandler<HTMLFormElement>;
  prompt: string;
  setPrompt: Dispatch<SetStateAction<string>>;
  onKeyDown: KeyboardEventHandler<HTMLInputElement>;
  loading: boolean;
}

interface UploadedImage {
  filename: string;
  public_url: string;
  s3_url?: string;
  upload_error?: string;
  file_type: string;
  original_name: string;
}

export default function InputForm({
  onSubmit,
  prompt,
  setPrompt,
  onKeyDown,
  loading,
}: Props) {
  const [uploading, setUploading] = useState(false);
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith("image/")) {
      alert("Please select an image file");
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert("Image size must be less than 10MB");
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://localhost:8000/upload/image", {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const result = await response.json();

      if (result.success) {
        // Add file type and original name to the uploaded image data
        const imageWithType = {
          ...result.data,
          file_type: file.type,
          original_name: file.name
        };
        setUploadedImages((prev) => [...prev, imageWithType]);
        // Clear the file input
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      } else {
        throw new Error(result.message || "Upload failed");
      }
    } catch (error) {
      console.error("Upload error:", error);
      alert("Failed to upload image. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const handleImageButtonClick = () => {
    fileInputRef.current?.click();
  };

  const removeUploadedImage = (index: number) => {
    setUploadedImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit: FormEventHandler<HTMLFormElement> = (e) => {
    e.preventDefault();

    // Call the original onSubmit handler with the attachments
    const formEvent = e as any;
    formEvent.attachments = uploadedImages.map(img => ({
      url: img.s3_url || img.public_url,
      file_type: img.file_type,
      friendly_name: img.original_name
    }));
    onSubmit(formEvent);

    // Clear the uploaded images after submission
    setUploadedImages([]);
  };

  return (
    <>
      {/* Input Form - Fixed */}
      <div className="border-t border-gray-200 p-6 flex-shrink-0 bg-white">
        <div className="max-w-4xl mx-auto">
          {/* Uploaded Images Preview */}
          {uploadedImages.length > 0 && (
            <div className="mb-4 space-y-2">
              {uploadedImages.map((image, index) => (
                <div key={index} className="p-3 border border-gray-300 rounded-xl bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gray-200 rounded-lg flex items-center justify-center">
                        <svg
                          className="w-6 h-6 text-gray-600"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                          />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          Image {index + 1} ready to send
                        </p>
                        <p className="text-xs text-gray-600">
                          {image.original_name || image.filename}
                        </p>
                        {image.upload_error && (
                          <p className="text-xs text-orange-600">
                            Note: {image.upload_error}
                          </p>
                        )}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeUploadedImage(index)}
                      className="text-gray-600 hover:text-gray-800"
                    >
                      <svg
                        className="w-5 h-5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <form onSubmit={handleSubmit}>
            <div className="flex flex-col">
              <input
                id="prompt-input"
                name="prompt"
                type="text"
                className="flex-1 px-4 py-3 bg-white border border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:border-transparent transition-all duration-200"
                placeholder="How can I help you today?"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={onKeyDown}
                autoFocus
              />
              <div className="flex flex-row justify-between mt-2 h-8">
                <button
                  type="button"
                  onClick={handleImageButtonClick}
                  disabled={uploading || loading}
                  className="px-3 py-2 rounded-xl font-medium transition-all duration-200 bg-gray-400 text-white hover:bg-gray-700 transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Upload Image"
                >
                  {uploading ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <div className="hover:cursor-pointer transition-transform duration-100 hover:scale-150">
                      <PlusIcon />
                    </div>
                  )}
                </button>
                <button
                  className="px-3 py-2 rounded-xl font-medium transition-all duration-200 bg-gray-400 text-white hover:bg-gray-700 transform hover:scale-105 active:scale-95"
                  type="submit"
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  ) : (
                    <div className="hover:cursor-pointer transition-transform duration-100 hover:scale-150">
                      <UpArrow />
                    </div>
                  )}
                </button>
              </div>
            </div>
          </form>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            className="hidden"
          />
        </div>
      </div>
    </>
  );
}
