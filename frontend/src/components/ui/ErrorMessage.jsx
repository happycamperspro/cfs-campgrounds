export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="rounded-lg bg-red-50 border border-red-200 p-6 text-center">
      <svg
        className="mx-auto h-10 w-10 text-red-400 mb-3"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <h3 className="text-sm font-medium text-red-800 mb-1">Something went wrong</h3>
      <p className="text-sm text-red-600">{message || 'An unexpected error occurred.'}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 btn-primary bg-red-600 hover:bg-red-700"
        >
          Try Again
        </button>
      )}
    </div>
  );
}
