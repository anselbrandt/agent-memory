interface Props {
  loading: boolean;
}

export default function LoadingSpinner({ loading }: Props) {
  return (
    <>
      {/* Loading Spinner - Fixed */}
      {loading && (
        <div className="flex justify-center py-4 flex-shrink-0 bg-white border-t border-gray-200">
          <div className="flex items-center gap-2 text-gray-600">
            <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
            <span className="text-sm">AI is thinking...</span>
          </div>
        </div>
      )}
    </>
  );
}
